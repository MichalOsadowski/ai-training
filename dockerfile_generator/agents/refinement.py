"""
Refinement Agent - Improves Dockerfiles based on build and validation failures.
"""

from typing import Optional
from dataclasses import dataclass

from ..llm.base import BaseLLMProvider

@dataclass
class RefinementResult:
    """Result of Dockerfile refinement."""
    improved_dockerfile: str
    changes_made: str
    reasoning: str

class RefinementAgent:
    """Refines Dockerfiles based on build/validation failures."""
    
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
    
    async def refine(
        self,
        original_dockerfile: str,
        build_error: Optional[str] = None,
        validation_error: Optional[str] = None,
        build_logs: Optional[str] = None
    ) -> RefinementResult:
        """Refine Dockerfile based on error feedback."""
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            original_dockerfile=original_dockerfile,
            build_error=build_error,
            validation_error=validation_error,
            build_logs=build_logs
        )
        
        response = await self.llm_provider.generate_with_system_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=2500
        )
        
        return self._parse_refinement_response(response.content)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for refinement."""
        return """You are an expert Docker engineer specializing in debugging and fixing Dockerfile issues.

        Your task is to analyze build failures, validation errors, and logs to improve Dockerfiles.

        CRITICAL REQUIREMENTS:
        1. Return your response in this EXACT format:
        
        IMPROVED_DOCKERFILE:
        [Complete improved Dockerfile content here]
        
        CHANGES_MADE:
        [List of specific changes made]
        
        REASONING:
        [Explanation of why these changes fix the issues]

        2. Focus on common Docker issues:
        - Missing dependencies
        - Incorrect base images
        - Permission issues
        - Path problems
        - Package installation failures
        - Runtime environment issues
        - Security vulnerabilities

        3. Always provide a complete, working Dockerfile
        4. Maintain the original intent while fixing issues
        5. Follow Docker best practices
        6. Be specific about what was changed and why
        """
    
    def _build_user_prompt(
        self,
        original_dockerfile: str,
        build_error: Optional[str],
        validation_error: Optional[str],
        build_logs: Optional[str]
    ) -> str:
        """Build user prompt with error context."""
        
        prompt = f"""Please analyze and fix the following Dockerfile issues:

        ORIGINAL DOCKERFILE:
        ```dockerfile
        {original_dockerfile}
        ```
        """
        
        if build_error:
            prompt += f"""
        BUILD ERROR:
        {build_error}
        """
        
        if validation_error:
            prompt += f"""
        VALIDATION ERROR:
        {validation_error}
        """
        
        if build_logs:
            prompt += f"""
        BUILD LOGS:
        {build_logs[-2000:]}  # Last 2000 chars to avoid token limit
        """
        
        prompt += """
        
        Please analyze these issues and provide an improved Dockerfile that addresses the problems.
        Focus on:
        1. Fixing build failures
        2. Resolving dependency issues
        3. Correcting configuration problems
        4. Improving security and best practices
        5. Ensuring the script can run properly
        
        Use the exact format specified in the system prompt.
        """
        
        return prompt
    
    def _parse_refinement_response(self, response: str) -> RefinementResult:
        """Parse refinement response into structured result."""
        
        # Initialize defaults
        improved_dockerfile = ""
        changes_made = "No specific changes identified"
        reasoning = "No reasoning provided"
        
        # Parse the structured response
        sections = response.split("IMPROVED_DOCKERFILE:")
        if len(sections) > 1:
            remaining = sections[1]
            
            # Extract Dockerfile
            changes_split = remaining.split("CHANGES_MADE:")
            if len(changes_split) > 1:
                improved_dockerfile = changes_split[0].strip()
                remaining = changes_split[1]
                
                # Extract changes
                reasoning_split = remaining.split("REASONING:")
                if len(reasoning_split) > 1:
                    changes_made = reasoning_split[0].strip()
                    reasoning = reasoning_split[1].strip()
                else:
                    changes_made = remaining.strip()
            else:
                improved_dockerfile = remaining.strip()
        
        # Fallback parsing if structured format not found
        if not improved_dockerfile and "FROM " in response:
            # Try to extract Dockerfile from code blocks
            if "```dockerfile" in response:
                start = response.find("```dockerfile") + len("```dockerfile")
                end = response.find("```", start)
                if end > start:
                    improved_dockerfile = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.rfind("```")
                if end > start:
                    improved_dockerfile = response[start:end].strip()
            else:
                # Try to find FROM instruction
                lines = response.split('\n')
                dockerfile_lines = []
                in_dockerfile = False
                
                for line in lines:
                    if line.strip().startswith('FROM '):
                        in_dockerfile = True
                    if in_dockerfile:
                        if any(line.strip().startswith(cmd) for cmd in [
                            'FROM', 'RUN', 'COPY', 'ADD', 'WORKDIR', 'EXPOSE', 
                            'ENV', 'CMD', 'ENTRYPOINT', 'VOLUME', 'USER', 'LABEL', 'ARG'
                        ]) or line.strip().startswith('#'):
                            dockerfile_lines.append(line)
                        elif line.strip() == "":
                            dockerfile_lines.append(line)
                        else:
                            break
                
                if dockerfile_lines:
                    improved_dockerfile = '\n'.join(dockerfile_lines).strip()
        
        # Clean up the Dockerfile
        improved_dockerfile = self._clean_dockerfile(improved_dockerfile)
        
        # If we still don't have a Dockerfile, create a basic one
        if not improved_dockerfile or not improved_dockerfile.startswith('FROM'):
            improved_dockerfile = self._create_fallback_dockerfile()
            changes_made = "Created fallback Dockerfile due to parsing issues"
            reasoning = "Could not parse AI response, created basic working Dockerfile"
        
        return RefinementResult(
            improved_dockerfile=improved_dockerfile,
            changes_made=changes_made,
            reasoning=reasoning
        )
    
    def _clean_dockerfile(self, dockerfile: str) -> str:
        """Clean and validate Dockerfile content."""
        
        if not dockerfile:
            return ""
        
        lines = dockerfile.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip empty lines at the beginning
            if not cleaned_lines and not line:
                continue
            # Keep the line
            cleaned_lines.append(line)
        
        # Ensure it starts with FROM
        if cleaned_lines and not cleaned_lines[0].startswith('FROM'):
            # Find the first FROM instruction
            for i, line in enumerate(cleaned_lines):
                if line.startswith('FROM'):
                    cleaned_lines = cleaned_lines[i:]
                    break
        
        return '\n'.join(cleaned_lines)
    
    def _create_fallback_dockerfile(self) -> str:
        """Create a basic fallback Dockerfile."""
        return """FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN chmod +x *.py *.sh *.js 2>/dev/null || true

CMD ["python", "--help"]""" 