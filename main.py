#!/usr/bin/env python3
"""
Main CLI interface for the Dockerfile Generator using LangGraph.

This tool generates Dockerfiles for scripts using AI agents with validation and refinement.
"""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import Optional

from dockerfile_generator.workflow import DockerfileGeneratorWorkflow
from dockerfile_generator.utils.budget_tracker import BudgetTracker


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    
    parser = argparse.ArgumentParser(
        description="Generate optimized Dockerfiles for Python, JavaScript, and Bash scripts using AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --api-key sk-your-api-key --script-path script.py
  %(prog)s --api-key sk-your-api-key --script-path script.py --example "python script.py 'hello world'"
  %(prog)s --api-key sk-your-api-key --script-path script.js --output ./docker_output --budget 2.0
  %(prog)s --api-key sk-your-api-key --script-path script.sh --example "bash script.sh 'test input'" --verbose

Supported Languages: Python (.py), JavaScript (.js, .mjs, .ts), Bash (.sh, .bash)
For more information, see: https://github.com/your-repo/ai-training
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--api-key",
        required=True,
        help="OpenAI API key for AI agents"
    )
    
    parser.add_argument(
        "--script-path", 
        required=True,
        help="Path to the script to containerize"
    )
    
    # Optional arguments
    parser.add_argument(
        "--example",
        "--example-usage",
        dest="example_usage",
        help="Example command showing how to run the script (e.g., 'python script.py arg1')"
    )
    
    parser.add_argument(
        "--output",
        "--output-dir",
        dest="output_dir",
        default="./docker_output",
        help="Directory to save the generated Dockerfile (default: ./docker_output)"
    )
    
    parser.add_argument(
        "--budget",
        type=float,
        default=0.10,
        help="Maximum budget for API calls in USD (default: 0.10)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output for debugging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Dockerfile Generator 1.0.0"
    )
    
    return parser


def validate_arguments(args) -> tuple[bool, Optional[str]]:
    """Validate command line arguments."""
    
    # Check if script file exists
    script_path = Path(args.script_path)
    if not script_path.exists():
        return False, f"Script file not found: {args.script_path}"
    
    if not script_path.is_file():
        return False, f"Path is not a file: {args.script_path}"
    
    # Check API key format (basic validation)
    if not args.api_key.startswith('sk-'):
        return False, "API key should start with 'sk-'. Please check your OpenAI API key."
    
    # Check budget
    if args.budget <= 0:
        return False, "Budget must be greater than 0"
    
    if args.budget > 5:
        return False, "Budget seems unusually high (>$5). Please confirm this is correct."
    
    return True, None


async def run_workflow(args) -> bool:
    """Run the Dockerfile generation workflow."""
    
    print("🤖 Dockerfile Generator using AI Agents")
    print("=" * 50)
    print(f"📝 Script: {args.script_path}")
    print(f"📁 Output: {args.output_dir}")
    print(f"💰 Budget: ${args.budget:.2f}")
    if args.example_usage:
        print(f"📋 Example: {args.example_usage}")
    print("=" * 50)
    
    try:
        # Initialize budget tracker
        budget_tracker = BudgetTracker(args.budget)
        
        # Create workflow
        workflow = DockerfileGeneratorWorkflow(
            api_key=args.api_key,
            budget_tracker=budget_tracker,
            verbose=args.verbose
        )
        
        # Run the workflow
        print("🚀 Starting Dockerfile generation workflow...")
        result = await workflow.run_async(
            script_path=args.script_path,
            example_usage=args.example_usage,
            output_dir=args.output_dir
        )
        
        # Display results
        print("\n" + "=" * 50)
        print("📊 WORKFLOW RESULTS")
        print("=" * 50)
        
        if result.success:
            print("✅ SUCCESS: Dockerfile generated and validated!")
            print(f"📄 Dockerfile: {result.dockerfile_path}")
            print(f"🐳 Docker image: {result.image_name}")
            
            if result.validation_results:
                print(f"\n🧪 Validation Results ({len(result.validation_results)} tests):")
                for i, test in enumerate(result.validation_results, 1):
                    status = "✅ PASS" if test.get('passed', False) else "❌ FAIL"
                    print(f"   {i}. {test.get('test_name', 'Unknown')}: {status}")
                    if not test.get('passed', False) and test.get('error'):
                        print(f"      Error: {test['error']}")
            
            print(f"\n💰 Total cost: ${result.total_cost:.4f}")
            
            # Instructions for using the generated Dockerfile
            print(f"\n📚 USAGE INSTRUCTIONS:")
            print(f"   1. Navigate to: {args.output_dir}")
            print(f"   2. Build image: docker build -t my-script .")
            print(f"   3. Run container: docker run my-script")
            if args.example_usage:
                # Extract arguments from example usage
                parts = args.example_usage.split()
                if len(parts) > 2:  # More than just "python script.py"
                    script_args = " ".join(parts[2:])
                    print(f"   4. With arguments: docker run my-script {script_args}")
            
        else:
            print("❌ FAILED: Could not generate working Dockerfile")
            print(f"❌ Error: {result.error}")
            print(f"💰 Cost incurred: ${result.total_cost:.4f}")
            
            # Show validation details if available
            if result.validation_results:
                print(f"\n🧪 Validation Details:")
                for test in result.validation_results:
                    if not test.get('passed', False):
                        print(f"   ❌ {test.get('test_name', 'Unknown')}: {test.get('error', 'No error details')}")
        
        print("=" * 50)
        return result.success
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Workflow interrupted by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    """Main entry point."""
    
    # Parse arguments
    parser = create_parser()
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Validate arguments
    valid, error_msg = validate_arguments(args)
    if not valid:
        print(f"❌ Error: {error_msg}")
        sys.exit(1)
    
    # Run the workflow
    try:
        success = asyncio.run(run_workflow(args))
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted")
        sys.exit(130)
        
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 