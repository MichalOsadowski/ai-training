# AI-Powered Dockerfile Generator

Automatically generates and validates Dockerfiles for any script using AI agents and LangGraph.

## 🚀 Features

- **Multi-Language Support**: Works with Python, JavaScript, and Bash scripts
- **AI-Powered Generation**: Uses OpenAI GPT models to create optimized Dockerfiles
- **Automated Validation**: Builds and tests Docker images automatically
- **Self-Healing**: Automatically refines Dockerfiles based on build/validation failures
- **Security-First**: Input validation and prompt injection protection
- **Budget Management**: Tracks API costs and enforces spending limits
- **LLM Vendor Agnostic**: Easy to extend with other LLM providers

## 🏗️ Architecture

The tool uses a LangGraph-based workflow with specialized AI agents:

```
Script → Analysis → Generation → Build → Validation → Success
           ↑                              ↓
           └─── Refinement Agent ←────────┘
```

### Agents

1. **Script Analyzer**: Detects language, dependencies, and requirements
2. **Dockerfile Generator**: Creates optimized Dockerfiles using AI
3. **Docker Builder**: Handles image building and error management
4. **Validation Agent**: Tests images against expected behavior
5. **Refinement Agent**: Iteratively improves failed builds

## 📋 Prerequisites

- Python 3.8+
- Docker installed and running
- OpenAI API key

## 🛠️ Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd ai-training
```

2. Install dependencies:

```bash
pip3 install -r requirements.txt
```

3. Verify Docker is running:

```bash
docker --version
```

## 💻 Usage

### Basic Usage

```bash
python3 main.py --api-key sk-your-openai-key --script-path path/to/your/script.py
```

### Advanced Usage

```bash
python3 main.py \
  --api-key sk-your-openai-key \
  --script-path ../Jit-ai-challenge/word_reverser.py \
  --example-usage "python word_reverser.py 'Hello World'" \
  --output-dir ./output \
  --budget 2.0 \
  --verbose
```

### Command Line Options

| Option            | Description                            | Default           |
| ----------------- | -------------------------------------- | ----------------- |
| `--api-key`       | OpenAI API key (required)              | -                 |
| `--script-path`   | Path to script to dockerize (required) | -                 |
| `--example-usage` | Example command for validation         | None              |
| `--output-dir`    | Output directory for generated files   | `./docker_output` |
| `--budget`  | Maximum budget in USD                  | `0.10`            |
| `--verbose`       | Enable verbose output                  | False             |

## 📊 Examples

### Python Script

```bash
python3 main.py \
  --api-key sk-... \
  --script-path ../Jit-ai-challenge/word_reverser.py \
  --example-usage "python word_reverser.py 'Hello World'"
```

### JavaScript Script

```bash
python3 main.py \
  --api-key sk-... \
  --script-path ../Jit-ai-challenge/vowel_counter.js \
  --example-usage "node vowel_counter.js 'Hello World'"
```

### Bash Script

```bash
python3 main.py \
  --api-key sk-... \
  --script-path ../Jit-ai-challenge/line_counter.sh \
  --example-usage "bash line_counter.sh 'Single line text'"
```

## 📁 Output Structure

After successful execution, you'll find:

```
docker_output/
├── Dockerfile          # Generated Dockerfile
├── word_reverser.py    # Your script (copied from source)
├── .dockerignore       # Auto-generated
└── build_logs.txt      # Build and validation logs
```

**✨ Complete Build Context**: The output directory contains everything needed for Docker builds, so you can run `docker build .` directly.

## 🔧 Generated Dockerfile Features

- **Security**: Non-root user, minimal permissions
- **Optimization**: Multi-stage builds, layer caching
- **Best Practices**: Specific version tags, .dockerignore
- **Language-Specific**: Optimized for each runtime
- **Dependencies**: Automatic package management

## 🧪 Testing Generated Docker Images

After generation, test your Docker image:

```bash
# Build the image
docker build -t my-script ./docker_output

# Run with example
docker run --rm my-script "Hello World"

# Interactive mode
docker run --rm -it my-script bash
```

## 💰 Cost Management

The tool includes built-in budget tracking:

- **Default Budget**: $0.10 (10 cents) per run - sufficient for most scripts
- **Typical Costs**: $0.01-$0.05 per simple script, $0.02-$0.08 for complex ones
- **Budget Enforcement**: Stops execution before exceeding limits
- **Cost Tracking**: Real-time spending updates with detailed breakdowns

The conservative 10-cent default ensures cost control while allowing successful processing of most scripts.

Example output:

```
💰 Total cost: $0.0234
📊 Budget: $0.0234/$0.10 (23.4%)
```

## 🔒 Security Features

- **Input Validation**: Validates script paths and content
- **Prompt Injection Protection**: Detects and blocks malicious prompts
- **Safe Dockerfile Generation**: Follows security best practices
- **Docker Context Validation**: Ensures safe build contexts

## 🚨 Error Handling

The tool includes comprehensive error handling:

1. **Build Failures**: Automatically retries with improvements
2. **Validation Failures**: Refines Dockerfiles based on test results
3. **Budget Limits**: Stops execution before exceeding budget
4. **Docker Issues**: Clear error messages for Docker problems

## 🔧 Configuration

### Environment Variables

```bash
export OPENAI_API_KEY=sk-your-key-here
export DOCKER_HOST=unix:///var/run/docker.sock  # Optional
```

### Custom LLM Providers

Extend the `BaseLLMProvider` class to add new providers:

```python
from dockerfile_generator.llm.base import BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    async def generate(self, messages, **kwargs):
        # Your implementation
        pass
```

## 📚 API Reference

### Main Classes

- `DockerfileGeneratorWorkflow`: Main orchestrator
- `ScriptAnalyzer`: Analyzes scripts for requirements
- `DockerfileGenerator`: AI-powered Dockerfile creation
- `DockerBuilder`: Handles Docker operations
- `ValidationAgent`: Tests generated images
- `RefinementAgent`: Improves failed builds

### Usage in Code

```python
from dockerfile_generator.workflow import DockerfileGeneratorWorkflow
from dockerfile_generator.utils.budget_tracker import BudgetTracker

# Initialize
budget_tracker = BudgetTracker(0.10)
workflow = DockerfileGeneratorWorkflow(
    api_key="sk-...",
    budget_tracker=budget_tracker,
    verbose=True
)

# Run
result = workflow.run(
    script_path="./script.py",
    example_usage="python script.py 'test'",
    output_dir="./output"
)

print(f"Success: {result.success}")
print(f"Cost: ${result.total_cost:.4f}")
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🐛 Troubleshooting

### Common Issues

**Docker not found**

```bash
# Make sure Docker is installed and running
docker --version
sudo systemctl start docker  # Linux
```

**Permission denied**

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

**API key issues**

```bash
# Verify your OpenAI API key
export OPENAI_API_KEY=sk-your-key
python -c "import openai; print('API key valid')"
```

**Build failures**

- Check Docker daemon is running
- Ensure sufficient disk space
- Verify internet connection for base image pulls

## 📞 Support

- **Issues**: GitHub Issues
- **Documentation**: This README
- **Examples**: See `examples/` directory

## 🎯 Roadmap

- [ ] Integration with CI/CD pipelines
- [ ] Web interface
- [ ] Batch processing
- [ ] Custom Dockerfile templates
- [ ] Performance optimizations
- [ ] Multi-architecture builds

---

**Made with ❤️ using AI and LangGraph**
