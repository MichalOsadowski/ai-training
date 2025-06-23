"""
Security utilities for input validation and prompt injection protection.
"""

import re
import os
from pathlib import Path
from typing import List, Set

class SecurityValidator:
    """Validates inputs and protects against security issues."""
    
    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        r"ignore\s+previous\s+instructions",
        r"ignore\s+the\s+above",
        r"forget\s+everything",
        r"new\s+instructions",
        r"system\s*:\s*",
        r"human\s*:\s*",
        r"assistant\s*:\s*",
        r"```\s*system",
        r"```\s*user",
        r"<\s*system\s*>",
        r"<\s*user\s*>",
        r"roleplay\s+as",
        r"pretend\s+to\s+be",
        r"act\s+as\s+if",
    ]
    
    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.msi', '.msp',
        '.reg', '.vb', '.vbs', '.js', '.jse', '.ws', '.wsf', '.wsh'
    }
    
    # Allowed script extensions for supported languages
    ALLOWED_EXTENSIONS = {
        '.py',      # Python
        '.js',      # JavaScript
        '.mjs',     # JavaScript modules
        '.ts',      # TypeScript (runs on Node)
        '.sh',      # Bash shell
        '.bash'     # Bash shell
    }
    
    def __init__(self):
        self.injection_regex = re.compile(
            '|'.join(self.INJECTION_PATTERNS), 
            re.IGNORECASE | re.MULTILINE
        )
    
    def validate_script_path(self, script_path: str) -> bool:
        """Validate script path for security."""
        try:
            path = Path(script_path)
            
            # Check if file exists
            if not path.exists():
                return False
            
            # Check if it's a file (not directory)
            if not path.is_file():
                return False
            
            # Check file extension
            if path.suffix.lower() in self.DANGEROUS_EXTENSIONS:
                return False
            
            # Check for path traversal attempts
            if '..' in str(path) or str(path).startswith('/'):
                # Allow absolute paths but be cautious
                resolved = path.resolve()
                if not self._is_safe_path(resolved):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is in safe locations."""
        path_str = str(path).lower()
        
        # Dangerous system directories
        dangerous_dirs = [
            '/system', '/windows', '/program files', '/boot',
            '/etc/passwd', '/etc/shadow', '/root', '/home'
        ]
        
        for dangerous in dangerous_dirs:
            if dangerous in path_str:
                return False
        
        return True
    
    def detect_prompt_injection(self, text: str) -> bool:
        """Detect potential prompt injection attempts."""
        if not text:
            return False
        
        # Check for common injection patterns
        if self.injection_regex.search(text):
            return True
        
        # Check for excessive special characters
        special_chars = sum(1 for c in text if c in '{}[]<>|`~!@#$%^&*()+=')
        if len(text) > 0 and special_chars / len(text) > 0.3:
            return True
        
        # Check for very long inputs (potential DoS)
        if len(text) > 10000:
            return True
        
        return False
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize input text."""
        if not text:
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Limit length
        if len(text) > 5000:
            text = text[:5000] + "..."
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def validate_docker_context(self, context_dir: str) -> bool:
        """Validate Docker build context directory."""
        try:
            path = Path(context_dir)
            
            # Must be a directory
            if not path.is_dir():
                return False
            
            # Check for dangerous files in context
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    if file_path.suffix.lower() in self.DANGEROUS_EXTENSIONS:
                        return False
                    
                    # Check file size (prevent huge files)
                    if file_path.stat().st_size > 50 * 1024 * 1024:  # 50MB limit
                        return False
            
            return True
            
        except Exception:
            return False
    
    def validate_example_usage(self, usage: str) -> bool:
        """Validate example usage command."""
        if not usage:
            return True  # Optional parameter
        
        # Check for prompt injection
        if self.detect_prompt_injection(usage):
            return False
        
        # Check for dangerous commands
        dangerous_commands = [
            'rm ', 'del ', 'format ', 'fdisk', 'mkfs',
            'sudo ', 'su ', 'chmod 777', 'curl ', 'wget ',
            'nc ', 'netcat', 'ssh ', 'scp ', 'rsync ',
            '&&', '||', ';', '|', '>', '>>', '<',
            '$(', '`', 'eval ', 'exec ', 'system('
        ]
        
        usage_lower = usage.lower()
        for dangerous in dangerous_commands:
            if dangerous in usage_lower:
                return False
        
        return True 