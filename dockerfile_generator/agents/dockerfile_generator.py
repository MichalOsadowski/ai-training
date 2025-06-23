"""
Dockerfile Generation Agent - Uses AI to generate optimized Dockerfiles.
"""

from typing import List, Optional
from pathlib import Path

from ..llm.base import BaseLLMProvider

class DockerfileGenerator:
    """Generates Dockerfiles using AI with best practices."""
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
    
    async def generate(
        self,
        language: str,
        runtime_version: Optional[str],
        dependencies: List[str],
        base_image: str,
        script_path: str,
        example_usage: Optional[str] = None
    ) -> str:
        """Generate optimized Dockerfile for the script."""
        
        script_name = Path(script_path).name
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            language=language,
            runtime_version=runtime_version,
            dependencies=dependencies,
            base_image=base_image,
            script_name=script_name,
            example_usage=example_usage
        )
        
        response = await self.llm_provider.generate_with_system_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        dockerfile_content = self._clean_dockerfile_response(response.content)
        return dockerfile_content
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt for Dockerfile generation."""
        return """You are an expert Docker and DevOps engineer specializing in creating optimized, secure, and production-ready Dockerfiles.

        CRITICAL REQUIREMENTS:
        1. Generate ONLY the Dockerfile content - no explanations or markdown
        2. Follow Docker best practices for security, performance, and maintainability
        3. Use multi-stage builds when beneficial
        4. Minimize image size and layers
        5. Set appropriate non-root user for security
        6. Use specific version tags, not 'latest'
        7. Copy only necessary files
        8. Set proper working directory
        9. Handle dependencies efficiently
        10. Use ENTRYPOINT for scripts that accept arguments (allows docker run image arg1 arg2)
        11. Include health checks where appropriate

        SECURITY PRACTICES:
        - Run as non-root user
        - Use specific version tags
        - Minimize attack surface
        - Don't expose unnecessary ports
        - Use .dockerignore patterns

        OPTIMIZATION PRACTICES:
        - Order layers by frequency of change
        - Use BuildKit optimizations
        - Leverage layer caching
        - Multi-stage builds for compiled languages
        - Alpine variants when possible

        OUTPUT FORMAT:
        Return ONLY the Dockerfile content, starting with 'FROM' and ending with the last instruction.
        """
    
    def _build_user_prompt(
        self,
        language: str,
        runtime_version: Optional[str],
        dependencies: List[str],
        base_image: str,
        script_name: str,
        example_usage: Optional[str]
    ) -> str:
        """Build user prompt with script-specific details."""
        
        prompt = f"""Generate a Dockerfile for this {language} script:

        Script: {script_name}
        Base Image: {base_image}
        Runtime Version: {runtime_version or 'latest stable'}
        Dependencies: {', '.join(dependencies) if dependencies else 'none detected'}
        
        DEPENDENCY STATUS: {"This script has external dependencies" if dependencies else "This is a standalone script with no external dependencies"}
        
        CRITICAL FOR BASH SCRIPTS: {f"This is a {language} script. You MUST use a base image that includes bash (like ubuntu:22.04, debian:bullseye-slim) OR install bash if using Alpine/minimal images." if language == 'bash' else ""}
        """
        
        if example_usage:
            prompt += f"\nExample Usage: {example_usage}"
        
        # Add language-specific guidance
        language_guidance = self._get_language_specific_guidance(language)
        if language_guidance:
            prompt += f"\n\nLanguage-specific considerations:\n{language_guidance}"
        
        prompt += """

        Requirements:
        1. Create a production-ready Dockerfile
        2. IMPORTANT: Use ENTRYPOINT instead of CMD to allow command line arguments to be passed
        3. Follow security best practices (non-root user, minimal permissions)
        4. Optimize for size and build speed
        5. Handle dependencies efficiently
        6. Set appropriate working directory and entry point
        7. Structure: Use ENTRYPOINT for the script execution to enable argument passing
        8. FOR BASH SCRIPTS: Ensure bash is available - either use ubuntu/debian base or install bash
        
        ENTRYPOINT vs CMD guidance:
        - Use ENTRYPOINT ["python", "script.py"] to allow: docker run image arg1 arg2
        - Use ENTRYPOINT ["node", "script.js"] for JavaScript files
        - Use ENTRYPOINT ["bash", "script.sh"] for bash scripts (most reliable)
        - CMD is only for default arguments or commands that don't expect user input
        
        Generate the Dockerfile content only:"""
        
        return prompt
    
    def _get_language_specific_guidance(self, language: str) -> str:
        """Get language-specific Dockerfile guidance for supported languages."""
        
        guidance = {
            'python': """
            - Use pip requirements.txt or pipenv if dependencies exist
            - Consider using python:slim or python:alpine variants
            - Set PYTHONPATH and PYTHONUNBUFFERED environment variables
            - Use pip install --no-cache-dir for smaller images
            - Handle both pip packages and system packages if needed
            """,
            
            'javascript': """
            - IMPORTANT: Only use package.json if it actually exists in the project
            - For standalone scripts with no dependencies, just copy the .js file and use node directly
            - If package.json exists: Copy package.json and package-lock.json, then run npm ci
            - If no package.json: Skip npm steps entirely, just copy the script file
            - Consider using node:alpine variants for smaller images
            - Set NODE_ENV=production only if using npm packages
            - For standalone scripts: COPY script.js . then ENTRYPOINT ["node", "script.js"]
            """,
            
            'bash': """
            - CRITICAL: Must use a base image that includes bash (ubuntu:22.04, debian:bullseye-slim, NOT Alpine)
            - IMPORTANT: For bash scripts, use ENTRYPOINT ["bash", "script.sh"] for reliable execution
            - If using Alpine-based images, must install bash: RUN apk add --no-cache bash
            - Alternative approach: Use sh instead with ENTRYPOINT ["sh", "script.sh"] for minimal images
            - RECOMMENDED: Use ubuntu:22.04 or debian:bullseye-slim base images (they include bash by default)
            - Install necessary system utilities only if the script needs them (curl, wget, etc.)
            - Handle potential package installations with apt-get if script requires additional tools
            - Example: FROM ubuntu:22.04, COPY script.sh ., ENTRYPOINT ["bash", "script.sh"]
            - AVOID: Alpine, minimal, or scratch images unless you install bash first
            """
        }
        
        return guidance.get(language, "")
    
    def _clean_dockerfile_response(self, response: str) -> str:
        """Clean and validate Dockerfile response."""
        
        # Remove markdown code blocks if present
        if '```dockerfile' in response:
            start = response.find('```dockerfile') + len('```dockerfile')
            end = response.find('```', start)
            response = response[start:end].strip()
        elif '```' in response:
            start = response.find('```') + 3
            end = response.rfind('```')
            response = response[start:end].strip()
        
        # Remove any explanatory text before/after
        lines = response.split('\n')
        dockerfile_lines = []
        in_dockerfile = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('FROM '):
                in_dockerfile = True
            if in_dockerfile:
                if line and not line.startswith('#') or (line.startswith('#') and 'FROM' in line):
                    dockerfile_lines.append(line)
                elif line.startswith('#'):
                    dockerfile_lines.append(line)  # Keep comments
            # Stop if we hit explanatory text
            if in_dockerfile and line and not any(line.startswith(cmd) for cmd in [
                'FROM', 'RUN', 'COPY', 'ADD', 'WORKDIR', 'EXPOSE', 'ENV', 
                'CMD', 'ENTRYPOINT', 'VOLUME', 'USER', 'LABEL', 'ARG', '#'
            ]):
                break
        
        result = '\n'.join(dockerfile_lines).strip()
        
        # Ensure it starts with FROM
        if not result.startswith('FROM'):
            lines = result.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith('FROM'):
                    result = '\n'.join(lines[i:])
                    break
        
        return result 