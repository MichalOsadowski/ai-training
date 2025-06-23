"""
Docker Builder Agent - Handles Docker image building and management.
"""

import docker
import asyncio
import uuid
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging

@dataclass
class BuildResult:
    """Result of Docker build operation."""
    success: bool
    image_name: str
    logs: str
    error: Optional[str] = None
    build_time: float = 0.0

class DockerBuilder:
    """Handles Docker operations for building and testing images."""
    
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
            # Test connection
            self.client.ping()
        except Exception as e:
            self.logger.error(f"Failed to initialize Docker client: {e}")
            raise Exception("Docker is not available. Please ensure Docker is installed and running.")
    
    async def build_image(
        self,
        dockerfile_path: str,
        context_dir: str,
        script_path: str,
        image_name: Optional[str] = None
    ) -> BuildResult:
        """Build Docker image from Dockerfile."""
        
        if not image_name:
            image_name = f"dockerfile-generator-{uuid.uuid4().hex[:8]}"
        
        # Prepare build context
        build_context = await self._prepare_build_context(dockerfile_path, context_dir, script_path)
        
        try:
            import time
            start_time = time.time()
            
            # Build image
            logs = []
            image, build_logs = self.client.images.build(
                path=build_context,
                tag=image_name,
                rm=True,  # Remove intermediate containers
                forcerm=True,  # Always remove intermediate containers
                pull=False,  # Don't pull base image if it exists locally
                nocache=False,  # Use cache for faster builds
                dockerfile="Dockerfile"
            )
            
            # Collect logs
            for log in build_logs:
                if 'stream' in log:
                    logs.append(log['stream'].strip())
                elif 'error' in log:
                    logs.append(f"ERROR: {log['error']}")
            
            build_time = time.time() - start_time
            logs_str = '\n'.join(logs)
            
            self.logger.info(f"Successfully built image: {image_name}")
            
            return BuildResult(
                success=True,
                image_name=image_name,
                logs=logs_str,
                build_time=build_time
            )
            
        except docker.errors.BuildError as e:
            error_msg = f"Docker build failed: {str(e)}"
            logs = []
            
            # Extract build logs from error
            if hasattr(e, 'build_log'):
                for log in e.build_log:
                    if 'stream' in log:
                        logs.append(log['stream'].strip())
                    elif 'error' in log:
                        logs.append(f"ERROR: {log['error']}")
            
            logs_str = '\n'.join(logs) if logs else str(e)
            
            self.logger.error(error_msg)
            return BuildResult(
                success=False,
                image_name=image_name,
                logs=logs_str,
                error=error_msg
            )
            
        except Exception as e:
            error_msg = f"Unexpected build error: {str(e)}"
            self.logger.error(error_msg)
            return BuildResult(
                success=False,
                image_name=image_name,
                logs="",
                error=error_msg
            )
        
        finally:
            # Cleanup build context
            if build_context and Path(build_context).exists():
                shutil.rmtree(build_context, ignore_errors=True)
    
    async def _prepare_build_context(self, dockerfile_path: str, context_dir: str, script_path: str) -> str:
        """Prepare Docker build context with necessary files."""
        
        # Create temporary build context
        temp_dir = tempfile.mkdtemp(prefix="dockerfile_gen_")
        build_context = Path(temp_dir)
        
        try:
            # Copy Dockerfile
            dockerfile_dest = build_context / "Dockerfile"
            shutil.copy2(dockerfile_path, dockerfile_dest)
            
            # Copy script
            script_name = Path(script_path).name
            script_dest = build_context / script_name
            shutil.copy2(script_path, script_dest)
            
            # Copy any additional files from context directory
            context_path = Path(context_dir)
            if context_path.exists():
                for item in context_path.iterdir():
                    if item.is_file() and item.name not in ["Dockerfile", script_name]:
                        shutil.copy2(item, build_context / item.name)
            
            # Create .dockerignore if it doesn't exist
            dockerignore_path = build_context / ".dockerignore"
            if not dockerignore_path.exists():
                dockerignore_content = """
# Ignore common development files
.git
.gitignore
*.pyc
__pycache__/
.pytest_cache/
.coverage
.env
.venv
venv/
node_modules/
.DS_Store
*.log
.idea/
.vscode/
*.swp
*.swo
*~
"""
                dockerignore_path.write_text(dockerignore_content.strip())
            
            return str(build_context)
            
        except Exception as e:
            # Cleanup on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise Exception(f"Failed to prepare build context: {str(e)}")
    
    async def run_container(
        self,
        image_name: str,
        command: Optional[str] = None,
        timeout: int = 30,
        environment: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Run container and return output."""
        
        container = None
        try:
            container = self.client.containers.run(
                image=image_name,
                command=command,
                detach=True,
                environment=environment or {},
                remove=False,  # Don't auto-remove - we'll do it manually
                stdout=True,
                stderr=True
            )
            
            # Wait for container to complete
            result = container.wait(timeout=timeout)
            exit_code = result['StatusCode']
            
            # Get logs before removing container
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            
            return {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'output': logs,
                'error': logs if exit_code != 0 else None
            }
            
        except docker.errors.ContainerError as e:
            return {
                'success': False,
                'exit_code': e.exit_status,
                'output': e.stderr.decode('utf-8') if e.stderr else "",
                'error': f"Container error: {str(e)}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'exit_code': -1,
                'output': "",
                'error': f"Runtime error: {str(e)}"
            }
        
        finally:
            # Clean up container
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    self.logger.warning(f"Failed to remove container {container.id}: {e}")
    
    def cleanup_image(self, image_name: str) -> bool:
        """Remove Docker image."""
        try:
            self.client.images.remove(image_name, force=True)
            self.logger.info(f"Removed image: {image_name}")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to remove image {image_name}: {e}")
            return False
    
    def list_images(self) -> list:
        """List all images with dockerfile-generator prefix."""
        try:
            images = self.client.images.list()
            generator_images = []
            
            for image in images:
                if image.tags:
                    for tag in image.tags:
                        if tag.startswith('dockerfile-generator-'):
                            generator_images.append({
                                'id': image.short_id,
                                'tag': tag,
                                'size': image.attrs.get('Size', 0),
                                'created': image.attrs.get('Created', '')
                            })
            
            return generator_images
            
        except Exception as e:
            self.logger.error(f"Failed to list images: {e}")
            return []
    
    def cleanup_all_generated_images(self) -> int:
        """Remove all generated images."""
        images = self.list_images()
        removed_count = 0
        
        for image in images:
            if self.cleanup_image(image['tag']):
                removed_count += 1
        
        return removed_count 