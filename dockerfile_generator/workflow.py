"""
Main LangGraph workflow for Dockerfile generation and validation.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import asyncio
import logging

from langgraph.graph import StateGraph, END
from langchain.schema import BaseMessage
from pydantic import BaseModel

from .agents.script_analyzer import ScriptAnalyzer
from .agents.dockerfile_generator import DockerfileGenerator
from .agents.docker_builder import DockerBuilder
from .agents.validator import ValidationAgent
from .agents.refinement import RefinementAgent
from .llm.openai_provider import OpenAIProvider
from .utils.budget_tracker import BudgetTracker

# Define the workflow state
class WorkflowState(BaseModel):
    script_path: str
    script_content: str
    example_usage: Optional[str] = None
    output_dir: str
    
    # Analysis results
    language: Optional[str] = None
    runtime_version: Optional[str] = None
    dependencies: List[str] = []
    base_image: Optional[str] = None
    
    # Generated content
    dockerfile_content: Optional[str] = None
    dockerfile_path: Optional[str] = None
    
    # Build results
    image_name: Optional[str] = None
    build_success: bool = False
    build_logs: Optional[str] = None
    build_error: Optional[str] = None
    
    # Validation results
    validation_passed: bool = False
    validation_results: List[Dict] = []
    validation_error: Optional[str] = None
    
    # Refinement
    refinement_count: int = 0
    max_refinements: int = 3
    
    # Workflow control
    current_step: str = "analyze"
    completed: bool = False
    error: Optional[str] = None
    messages: List[str] = []

@dataclass
class WorkflowResult:
    success: bool
    dockerfile_path: Optional[str] = None
    image_name: Optional[str] = None
    validation_results: List[Dict] = None
    total_cost: float = 0.0
    error: Optional[str] = None

class DockerfileGeneratorWorkflow:
    """Main workflow orchestrator using LangGraph."""
    
    def __init__(self, api_key: str, budget_tracker: BudgetTracker, verbose: bool = False):
        self.llm_provider = OpenAIProvider(api_key, budget_tracker)
        self.budget_tracker = budget_tracker
        self.verbose = verbose
        self.logger = logging.getLogger(__name__)
        
        # Initialize agents
        self.script_analyzer = ScriptAnalyzer(self.llm_provider)
        self.dockerfile_generator = DockerfileGenerator(self.llm_provider)
        self.docker_builder = DockerBuilder()
        self.validator = ValidationAgent(self.docker_builder)
        self.refinement_agent = RefinementAgent(self.llm_provider)
        
        # Build the workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("analyze", self._analyze_script)
        workflow.add_node("generate", self._generate_dockerfile)
        workflow.add_node("build", self._build_image)
        workflow.add_node("validate", self._validate_image)
        workflow.add_node("refine", self._refine_dockerfile)
        workflow.add_node("complete", self._complete_workflow)
        
        # Define the workflow edges
        workflow.set_entry_point("analyze")
        
        workflow.add_edge("analyze", "generate")
        workflow.add_edge("generate", "build")
        
        # Conditional edge from build
        workflow.add_conditional_edges(
            "build",
            self._should_validate_or_refine,
            {
                "validate": "validate",
                "refine": "refine",
                "complete": "complete"
            }
        )
        
        # Conditional edge from validate
        workflow.add_conditional_edges(
            "validate",
            self._should_complete_or_refine,
            {
                "complete": "complete",
                "refine": "refine"
            }
        )
        
        workflow.add_edge("refine", "generate")
        workflow.add_edge("complete", END)
        
        # Compile with recursion limit to prevent infinite loops
        return workflow.compile(debug=self.verbose)
    
    async def _analyze_script(self, state: WorkflowState) -> WorkflowState:
        """Analyze the input script to determine requirements."""
        try:
            if self.verbose:
                print("🔍 Analyzing script...")
            
            analysis = await self.script_analyzer.analyze(
                script_path=state.script_path,
                script_content=state.script_content
            )
            
            state.language = analysis.language
            state.runtime_version = analysis.runtime_version
            state.dependencies = analysis.dependencies
            state.base_image = analysis.recommended_base_image
            state.current_step = "generate"
            state.messages.append(f"Analysis complete: {analysis.language} script")
            
            return state
            
        except Exception as e:
            error_msg = str(e)
            # Check for API authentication errors
            if "authentication failed" in error_msg.lower() or "401" in error_msg:
                state.error = "OpenAI API authentication failed. Please check your API key."
            elif "rate limit" in error_msg.lower():
                state.error = "OpenAI API rate limit exceeded. Please try again later."
            else:
                state.error = f"Script analysis failed: {error_msg}"
            state.current_step = "complete"
            return state
    
    async def _generate_dockerfile(self, state: WorkflowState) -> WorkflowState:
        """Generate Dockerfile using AI."""
        try:
            if self.verbose:
                print("🐳 Generating Dockerfile...")
            
            dockerfile_content = await self.dockerfile_generator.generate(
                language=state.language,
                runtime_version=state.runtime_version,
                dependencies=state.dependencies,
                base_image=state.base_image,
                script_path=state.script_path,
                example_usage=state.example_usage
            )
            
            # Ensure output directory exists
            output_path = Path(state.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save Dockerfile
            dockerfile_path = output_path / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)
            
            # Copy script file to output directory so Dockerfile can reference it
            script_source = Path(state.script_path)
            script_dest = output_path / script_source.name
            import shutil
            shutil.copy2(script_source, script_dest)
            
            state.dockerfile_content = dockerfile_content
            state.dockerfile_path = str(dockerfile_path)
            state.current_step = "build"
            state.messages.append(f"Dockerfile and script copied to {state.output_dir}")
            
            return state
            
        except Exception as e:
            error_msg = str(e)
            # Check for API authentication errors
            if "authentication failed" in error_msg.lower() or "401" in error_msg:
                state.error = "OpenAI API authentication failed. Please check your API key."
            elif "rate limit" in error_msg.lower():
                state.error = "OpenAI API rate limit exceeded. Please try again later."
            else:
                state.error = f"Dockerfile generation failed: {error_msg}"
            state.current_step = "complete"
            return state
    
    async def _build_image(self, state: WorkflowState) -> WorkflowState:
        """Build Docker image."""
        try:
            if self.verbose:
                print("🔨 Building Docker image...")
            
            build_result = await self.docker_builder.build_image(
                dockerfile_path=state.dockerfile_path,
                context_dir=state.output_dir,
                script_path=state.script_path
            )
            
            state.build_success = build_result.success
            state.build_logs = build_result.logs
            state.build_error = build_result.error
            state.image_name = build_result.image_name
            
            if build_result.success:
                state.current_step = "validate"
                state.messages.append(f"Image built successfully: {build_result.image_name}")
            else:
                state.current_step = "refine"
                state.messages.append(f"Build failed: {build_result.error}")
            
            return state
            
        except Exception as e:
            state.error = f"Docker build failed: {str(e)}"
            state.current_step = "complete"
            return state
    
    async def _validate_image(self, state: WorkflowState) -> WorkflowState:
        """Validate the built Docker image."""
        try:
            if self.verbose:
                print("✅ Validating Docker image...")
            
            validation_result = await self.validator.validate(
                image_name=state.image_name,
                example_usage=state.example_usage,
                expected_behavior=state.script_content,
                script_path=state.script_path
            )
            
            state.validation_passed = validation_result.passed
            # Convert TestResult objects to dictionaries for Pydantic validation
            state.validation_results = [
                {
                    "test_name": test.test_name,
                    "passed": test.passed,
                    "output": test.output,
                    "expected": test.expected,
                    "error": test.error
                }
                for test in validation_result.test_results
            ]
            
            # Set validation error - if no general error, create one from failed tests
            if validation_result.error:
                state.validation_error = validation_result.error
            elif not validation_result.passed:
                # Generate error message from failed tests
                failed_tests = [test for test in validation_result.test_results if not test.passed]
                if failed_tests:
                    failed_test_names = [test.test_name for test in failed_tests]
                    failed_test_errors = [test.error for test in failed_tests if test.error]
                    
                    error_msg = f"Validation failed: {', '.join(failed_test_names)} tests failed"
                    if failed_test_errors:
                        error_msg += f". Errors: {'; '.join(failed_test_errors)}"
                    
                    state.validation_error = error_msg
                else:
                    state.validation_error = "Validation failed for unknown reasons"
            else:
                state.validation_error = None
            
            if validation_result.passed:
                state.current_step = "complete"
                state.messages.append("Validation passed successfully")
            else:
                state.current_step = "refine"
                state.messages.append(f"Validation failed: {state.validation_error}")
            
            return state
            
        except Exception as e:
            state.error = f"Validation failed: {str(e)}"
            state.current_step = "complete"
            return state
    
    async def _refine_dockerfile(self, state: WorkflowState) -> WorkflowState:
        """Refine Dockerfile based on build/validation failures."""
        try:
            if state.refinement_count >= state.max_refinements:
                state.error = f"Maximum refinement attempts ({state.max_refinements}) reached without success"
                state.current_step = "complete"
                return state
            
            if self.verbose:
                print(f"🔧 Refining Dockerfile (attempt {state.refinement_count + 1})...")
            
            refinement = await self.refinement_agent.refine(
                original_dockerfile=state.dockerfile_content,
                build_error=state.build_error,
                validation_error=state.validation_error,
                build_logs=state.build_logs
            )
            
            state.dockerfile_content = refinement.improved_dockerfile
            state.refinement_count += 1
            state.current_step = "generate"
            state.messages.append(f"Dockerfile refined (attempt {state.refinement_count})")
            
            return state
            
        except Exception as e:
            error_msg = str(e)
            # Check for API authentication errors - stop retrying if auth fails
            if "authentication failed" in error_msg.lower() or "401" in error_msg:
                state.error = "OpenAI API authentication failed. Please check your API key."
            elif "rate limit" in error_msg.lower():
                state.error = "OpenAI API rate limit exceeded. Please try again later."
            else:
                state.error = f"Refinement failed: {error_msg}"
            state.current_step = "complete"
            return state
    
    async def _complete_workflow(self, state: WorkflowState) -> WorkflowState:
        """Complete the workflow."""
        state.completed = True
        state.current_step = "completed"
        
        if state.validation_passed and not state.error:
            state.messages.append("Workflow completed successfully")
        else:
            # Provide better error information if missing
            if not state.error:
                if not state.build_success:
                    state.error = state.build_error or "Build failed without specific error"
                elif not state.validation_passed:
                    state.error = state.validation_error or "Validation failed without specific error"
                else:
                    state.error = "Workflow failed for unknown reasons"
            
            state.messages.append(f"Workflow completed with errors: {state.error}")
        
        return state
    
    def _should_validate_or_refine(self, state: WorkflowState) -> str:
        """Decide whether to validate, refine, or complete after build."""
        if not state.build_success:
            if state.refinement_count < state.max_refinements:
                return "refine"
            else:
                return "complete"
        return "validate"
    
    def _should_complete_or_refine(self, state: WorkflowState) -> str:
        """Decide whether to complete or refine after validation."""
        if not state.validation_passed:
            if state.refinement_count < state.max_refinements:
                return "refine"
        return "complete"
    
    def run(self, script_path: str, example_usage: Optional[str], output_dir: str) -> WorkflowResult:
        """Run the complete workflow synchronously."""
        return asyncio.run(self.run_async(script_path, example_usage, output_dir))
    
    async def run_async(self, script_path: str, example_usage: Optional[str], output_dir: str) -> WorkflowResult:
        """Run the complete workflow asynchronously."""
        try:
            # Read script content
            script_content = Path(script_path).read_text()
            
            # Initialize state
            initial_state = WorkflowState(
                script_path=script_path,
                script_content=script_content,
                example_usage=example_usage,
                output_dir=output_dir
            )
            
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # LangGraph returns AddableValuesDict, access as dictionary
            validation_passed = final_state.get("validation_passed", False)
            error = final_state.get("error")
            build_success = final_state.get("build_success", False)
            current_step = final_state.get("current_step", "unknown")
            messages = final_state.get("messages", [])
            
            # Debug information
            if self.verbose:
                print(f"🔍 Final state debug:")
                print(f"   - Current step: {current_step}")
                print(f"   - Build success: {build_success}")
                print(f"   - Validation passed: {validation_passed}")
                print(f"   - Error: {error}")
                print(f"   - Messages: {messages}")
            
            # Determine better error message if none provided
            if not validation_passed and not error:
                if not build_success:
                    error = final_state.get("build_error") or "Docker build failed with unknown error"
                elif validation_passed is False:
                    error = final_state.get("validation_error") or "Validation failed with unknown error"
                else:
                    error = "Workflow failed at an unknown step"
            
            # Return result
            return WorkflowResult(
                success=validation_passed and not error,
                dockerfile_path=final_state.get("dockerfile_path"),
                image_name=final_state.get("image_name"),
                validation_results=final_state.get("validation_results", []),
                total_cost=self.budget_tracker.total_cost,
                error=error
            )
            
        except Exception as e:
            error_msg = str(e)
            # Handle specific error types
            if "recursion limit" in error_msg.lower():
                error_msg = "Workflow got stuck in a loop. This usually indicates an API authentication issue or repeated failures. Please check your API key and try again."
            elif "authentication failed" in error_msg.lower() or "401" in error_msg:
                error_msg = "OpenAI API authentication failed. Please check your API key."
            elif "rate limit" in error_msg.lower():
                error_msg = "OpenAI API rate limit exceeded. Please try again later."
            
            return WorkflowResult(
                success=False,
                total_cost=self.budget_tracker.total_cost,
                error=error_msg
            ) 