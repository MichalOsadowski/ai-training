"""
Script Analysis Agent - Analyzes scripts to determine runtime requirements.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..llm.base import BaseLLMProvider

@dataclass
class ScriptAnalysis:
    """Results of script analysis."""
    language: str
    runtime_version: Optional[str]
    dependencies: List[str]
    recommended_base_image: str
    entry_command: str
    additional_packages: Optional[List[str]] = None
    environment_vars: Optional[Dict[str, str]] = None

class ScriptAnalyzer:
    """Analyzes scripts to determine Docker requirements."""
    
    # Language detection patterns - Support for Python, JavaScript, and Bash only
    LANGUAGE_PATTERNS = {
        'python': [r'#!/usr/bin/env python', r'#!/usr/bin/python', r'import ', r'from .* import', r'def ', r'if __name__'],
        'javascript': [r'#!/usr/bin/env node', r'#!/usr/bin/node', r'require\(', r'console\.log', r'function ', r'const ', r'let ', r'var '],
        'bash': [r'#!/bin/bash', r'#!/bin/sh', r'#!/usr/bin/env bash', r'echo ', r'if \[', r'for .*in']
    }
    
    # Base images for supported languages
    BASE_IMAGES = {
        'python': 'python:3.11-slim',
        'javascript': 'node:18-alpine',
        'bash': 'ubuntu:22.04'
    }
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
    
    async def analyze(self, script_path: str, script_content: str) -> ScriptAnalysis:
        """Analyze script to determine requirements."""
        
        # Basic language detection
        language = self._detect_language(script_content, script_path)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(script_content, language)
        
        # Use AI for advanced analysis
        ai_analysis = await self._ai_enhanced_analysis(script_content, language, script_path)
        
        # Determine base image
        base_image = ai_analysis.get('base_image') or self.BASE_IMAGES.get(language, 'ubuntu:22.04')
        
        # For bash scripts, ensure base image supports bash or fallback to ubuntu
        if language == 'bash':
            bash_incompatible_patterns = ['alpine', 'scratch', 'busybox', 'distroless']
            if any(pattern in base_image.lower() for pattern in bash_incompatible_patterns):
                # Override with bash-compatible base image
                base_image = 'ubuntu:22.04'
        
        # Determine runtime version
        runtime_version = ai_analysis.get('runtime_version') or self._detect_runtime_version(script_content, language)
        
        # Generate entry command
        entry_command = self._generate_entry_command(script_path, language)
        
        return ScriptAnalysis(
            language=language,
            runtime_version=runtime_version,
            dependencies=dependencies,
            recommended_base_image=base_image,
            entry_command=entry_command,
            additional_packages=ai_analysis.get('additional_packages', []),
            environment_vars=ai_analysis.get('environment_vars', {})
        )
    
    def _detect_language(self, content: str, script_path: str) -> str:
        """Detect programming language from content and filename."""
        
        # Check file extension first
        path = Path(script_path)
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.mjs': 'javascript',
            '.ts': 'javascript',  # TypeScript runs on Node
            '.sh': 'bash',
            '.bash': 'bash'
        }
        
        if path.suffix.lower() in ext_map:
            return ext_map[path.suffix.lower()]
        
        # For files without recognized extensions, check content patterns
        # but only for supported languages
        content_lower = content.lower()
        scores: Dict[str, int] = {}
        
        for language, patterns in self.LANGUAGE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content, re.IGNORECASE | re.MULTILINE))
                score += matches
            scores[language] = score
        
        # Return language with highest score, but only if it has a reasonable score
        if scores and max(scores.values()) > 0:
            detected = max(scores.items(), key=lambda x: x[1])[0]
            return detected
        
        # No supported language detected - this should trigger an error
        return 'unsupported'
    
    def _extract_dependencies(self, content: str, language: str) -> List[str]:
        """Extract dependencies based on language."""
        dependencies = []
        
        if language == 'python':
            # Extract imports
            import_patterns = [
                r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                r'from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import'
            ]
            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                dependencies.extend(matches)
                
        elif language == 'javascript':
            # Extract requires
            require_pattern = r'require\([\'"]([^\'\"]+)[\'\"]\)'
            matches = re.findall(require_pattern, content)
            dependencies.extend(matches)
            
            # Extract ES6 imports
            import_pattern = r'import.*from\s+[\'"]([^\'\"]+)[\'"]'
            matches = re.findall(import_pattern, content)
            dependencies.extend(matches)
            

        
        # Remove duplicates and common stdlib modules
        return list(set(dep for dep in dependencies if dep and not self._is_stdlib_module(dep, language)))
    
    def _is_stdlib_module(self, module: str, language: str) -> bool:
        """Check if module is part of standard library."""
        stdlib_modules = {
            'python': {'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 're', 'math', 'random', 'collections'},
            'javascript': {'fs', 'path', 'http', 'https', 'url', 'querystring', 'crypto', 'util'},
            'bash': set()  # Bash doesn't have a module system like Python/JS
        }
        
        return module in stdlib_modules.get(language, set())
    
    def _detect_runtime_version(self, content: str, language: str) -> Optional[str]:
        """Detect specific runtime version requirements."""
        
        if language == 'python':
            # Look for version specifiers
            if 'python_requires' in content:
                match = re.search(r'python_requires\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                if match:
                    return match.group(1)
            
            # Check for Python 2 vs 3 indicators
            if any(keyword in content for keyword in ['print(', 'f"', 'f\'', '//']):
                return '3.11'
            elif 'print ' in content and 'print(' not in content:
                return '2.7'
                
        elif language == 'javascript':
            # Look for package.json content or Node-specific features
            if 'async/await' in content or 'const ' in content or 'let ' in content:
                return '18'
            else:
                return '16'
        
        return None
    
    def _generate_entry_command(self, script_path: str, language: str) -> str:
        """Generate Docker entry command."""
        filename = Path(script_path).name
        
        commands = {
            'python': f'python {filename}',
            'javascript': f'node {filename}',
            'bash': f'bash {filename}'
        }
        
        return commands.get(language, f'./{filename}')
    
    async def _ai_enhanced_analysis(self, content: str, detected_language: str, script_path: str) -> Dict[str, Any]:
        """Use AI to enhance analysis with advanced insights."""
        
        system_prompt = """You are an expert DevOps engineer analyzing scripts for containerization.
        Analyze the provided script and return a JSON response with the following structure:
        {
            "base_image": "recommended Docker base image",
            "runtime_version": "specific version if detectable",
            "additional_packages": ["list", "of", "system", "packages", "needed"],
            "environment_vars": {"KEY": "value"},
            "security_considerations": ["list of potential security issues"],
            "optimization_suggestions": ["list of optimization tips"]
        }
        
        Focus on:
        1. Detecting specific version requirements
        2. Identifying system-level dependencies
        3. Security best practices
        4. Performance optimizations
        
        CRITICAL: For bash scripts, only recommend base images that include bash by default (ubuntu, debian, centos) 
        or include bash installation steps. NEVER recommend Alpine, minimal, or scratch images for bash scripts 
        without bash installation instructions.
        """
        
        user_prompt = f"""Analyze this {detected_language} script for Docker containerization:

        Script path: {script_path}
        Script content:
        ```{detected_language}
        {content[:2000]}  # Limit content to avoid token overuse
        ```
        
        Provide analysis as valid JSON only."""
        
        try:
            response = await self.llm_provider.generate_with_system_prompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse JSON response
            import json
            analysis = json.loads(response.content)
            return analysis
            
        except Exception as e:
            # Fallback to basic analysis if AI fails
            return {
                "base_image": self.BASE_IMAGES.get(detected_language, 'ubuntu:22.04'),
                "runtime_version": None,
                "additional_packages": [],
                "environment_vars": {},
                "security_considerations": [],
                "optimization_suggestions": []
            } 