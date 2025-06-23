#!/usr/bin/env python3
"""
Example usage script for the Dockerfile Generator.
This demonstrates how to use the tool with the provided sample scripts.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def show_usage(api_key=None):
    """Show usage examples."""
    print("🐳 Dockerfile Generator - Example Usage")
    print("=" * 50)
    
    api_key_display = api_key if api_key else "sk-your-openai-key-here"
    
    print("\n1. Python Script Example:")
    print("python3 main.py \\")
    print(f"  --api-key {api_key_display} \\")
    print("  --script-path ../Jit-ai-challenge/word_reverser.py \\")
    print("  --example-usage \"python word_reverser.py 'Hello World'\" \\")
    print("  --output-dir ./docker_output_python")
    
    print("\n2. JavaScript Script Example:")
    print("python3 main.py \\")
    print(f"  --api-key {api_key_display} \\")
    print("  --script-path ../Jit-ai-challenge/vowel_counter.js \\")
    print("  --example-usage \"node vowel_counter.js 'Hello World'\" \\")
    print("  --output-dir ./docker_output_javascript")
    
    print("\n3. Bash Script Example:")
    print("python3 main.py \\")
    print(f"  --api-key {api_key_display} \\")
    print("  --script-path ../Jit-ai-challenge/line_counter.sh \\")
    print("  --example-usage \"bash line_counter.sh 'Single line text'\" \\")
    print("  --output-dir ./docker_output_bash")
    
    print("\n4. Advanced Usage with Custom Settings:")
    print("python3 main.py \\")
    print(f"  --api-key {api_key_display} \\")
    print("  --script-path ../Jit-ai-challenge/word_reverser.py \\")
    print("  --example-usage \"python word_reverser.py 'Hello World'\" \\")
    print("  --output-dir ./docker_output_advanced \\")
    print("  --budget 0.10 \\")
    print("  --verbose")
    
    print("\n📋 Prerequisites:")
    print("- Set your OpenAI API key")
    print("- Ensure Docker is installed and running")
    print("- Install requirements: pip install -r requirements.txt")
    
    print("\n🔧 Testing the Generated Docker Image:")
    print("# After successful generation:")
    print("docker build -t my-script ./docker_output")
    print("docker run --rm my-script 'Hello World'")
    
    print("\n💡 Tips:")
    print("- Use --verbose flag to see detailed progress")
    print("- The tool will automatically retry failed builds")
    print("- Budget tracking prevents overspending on API calls")
    print("- Generated Dockerfiles follow security best practices")
    
    if api_key:
        print(f"\n🚀 Ready to run! Your API key is configured.")
        print("Use --run-example <number> to execute one of the examples above.")
    else:
        print(f"\n🔑 To run examples, provide your API key:")
        print("python3 example_usage.py --api-key sk-your-key-here --run-example 1")

def check_prerequisites():
    """Check if prerequisites are met."""
    print("\n🔍 Checking Prerequisites...")
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append("Python 3.8+ required")
    else:
        print("✅ Python version OK")
    
    # Check if requirements.txt exists
    if not Path("requirements.txt").exists():
        issues.append("requirements.txt not found")
    else:
        print("✅ requirements.txt found")
    
    # Check if Docker is available
    try:
        import docker
        client = docker.from_env()
        client.ping()
        print("✅ Docker is available")
    except Exception:
        issues.append("Docker not available or not running")
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OpenAI API key not set in environment")
        print("   You'll need to provide it via --api-key parameter")
    else:
        print("✅ OpenAI API key found in environment")
    
    # Check if sample scripts exist
    sample_scripts = [
        "../Jit-ai-challenge/word_reverser.py",
        "../Jit-ai-challenge/vowel_counter.js", 
        "../Jit-ai-challenge/line_counter.sh"
    ]
    
    available_scripts = []
    for script in sample_scripts:
        if Path(script).exists():
            available_scripts.append(script)
    
    if available_scripts:
        print(f"✅ Found {len(available_scripts)} sample scripts")
    else:
        issues.append("No sample scripts found in parent directory")
    
    if issues:
        print(f"\n❌ Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("\n🎉 All prerequisites met!")
        return True

def run_example(example_number, api_key, verbose=False):
    """Run a specific example."""
    examples = {
        1: {
            "name": "Python Script (word_reverser.py)",
            "script_path": "../Jit-ai-challenge/word_reverser.py",
            "example_usage": "python word_reverser.py 'Hello World'",
            "output_dir": "./docker_output_python",
            "verbose": True
        },
        2: {
            "name": "JavaScript Script (vowel_counter.js)",
            "script_path": "../Jit-ai-challenge/vowel_counter.js",
            "example_usage": "node vowel_counter.js 'Hello World'",
            "output_dir": "./docker_output_javascript",
            "verbose": True
        },
        3: {
            "name": "Bash Script (line_counter.sh)",
            "script_path": "../Jit-ai-challenge/line_counter.sh",
            "example_usage": "bash line_counter.sh 'Single line text'",
            "output_dir": "./docker_output_bash",
            "verbose": True
        },
        4: {
            "name": "Advanced Python Script (with custom settings)",
            "script_path": "../Jit-ai-challenge/word_reverser.py",
            "example_usage": "python word_reverser.py 'Hello World'",
            "output_dir": "./docker_output_advanced",
            "budget": "0.10",
            "verbose": True
        }
    }
    
    if example_number not in examples:
        print(f"❌ Invalid example number: {example_number}")
        print("Available examples: 1, 2, 3, 4")
        return False
    
    example = examples[example_number]
    
    print(f"🚀 Running Example {example_number}: {example['name']}")
    print("=" * 60)
    
    # Check if script exists
    if not Path(example['script_path']).exists():
        print(f"❌ Script not found: {example['script_path']}")
        return False
    
    # Build command
    cmd = [
        "python3", "main.py",
        "--api-key", api_key,
        "--script-path", example['script_path'],
        "--example-usage", example['example_usage'],
        "--output-dir", example['output_dir']
    ]
    
    # Add advanced options for example 4
    if example_number == 4:
        cmd.extend(["--budget", example['budget']])
        cmd.append("--verbose")
    elif verbose:
        cmd.append("--verbose")
    
    print(f"Command: {' '.join(cmd)}")
    print()
    
    try:
        # Run the command
        result = subprocess.run(cmd, check=False, capture_output=False)
        
        if result.returncode == 0:
            print(f"\n✅ Example {example_number} completed successfully!")
            print(f"📁 Output saved to: {example['output_dir']}")
            return True
        else:
            print(f"\n❌ Example {example_number} failed with exit code: {result.returncode}")
            return False
            
    except KeyboardInterrupt:
        print(f"\n⚠️ Example {example_number} interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error running example {example_number}: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Dockerfile Generator - Example Usage and Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 example_usage.py                           # Show usage examples
  python3 example_usage.py --check                   # Check prerequisites  
  python3 example_usage.py --api-key sk-... --run-example 1  # Run Python example
  python3 example_usage.py --api-key sk-... --run-example 2 --verbose  # Run JS example with verbose output
        """
    )
    
    parser.add_argument('--api-key', help='OpenAI API key')
    parser.add_argument('--run-example', type=int, choices=[1, 2, 3, 4], 
                       help='Run a specific example (1-4)')
    parser.add_argument('--check', action='store_true', 
                       help='Check prerequisites')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output when running examples')
    
    args = parser.parse_args()
    
    if args.check:
        check_prerequisites()
    elif args.run_example:
        if not args.api_key:
            print("❌ API key is required to run examples.")
            print("Usage: python3 example_usage.py --api-key sk-your-key --run-example 1")
            sys.exit(1)
        
        success = run_example(args.run_example, args.api_key, args.verbose)
        sys.exit(0 if success else 1)
    else:
        show_usage(args.api_key)
        print("\nOptions:")
        print("  --check                     Check prerequisites")
        print("  --api-key KEY --run-example N  Run example N (1-4)")
        print("  --verbose                   Enable verbose output")

if __name__ == "__main__":
    main() 