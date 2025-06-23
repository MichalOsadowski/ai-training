# 🐳 Dockerfile Generator - Usage Examples

This document provides comprehensive examples of how to use the AI-powered Dockerfile generator tool.

## 🚀 Quick Start

### 1. Interactive Examples Script

The easiest way to get started is using the interactive examples script:

```bash
# Show all available examples
python3 example_usage.py

# Check if your system is ready
python3 example_usage.py --check

# Run a specific example (requires API key)
python3 example_usage.py --api-key sk-your-openai-key --run-example 1

# Run with verbose output
python3 example_usage.py --api-key sk-your-key --run-example 2 --verbose
```

### 2. Direct Tool Usage

You can also run the tool directly:

```bash
python3 main.py \
  --api-key sk-your-openai-key \
  --script-path ../Jit-ai-challenge/word_reverser.py \
  --example-usage "python word_reverser.py 'Hello World'" \
  --output-dir ./my_output
```

## 📋 Available Examples

### Example 1: Python Script (word_reverser.py)

- **Output Directory**: `./docker_output_python`
- **Script**: Word reverser that reverses word order in text
- **Example Usage**: `python word_reverser.py 'Hello World'`

### Example 2: JavaScript Script (vowel_counter.js)

- **Output Directory**: `./docker_output_javascript`
- **Script**: Counts vowels in input text
- **Example Usage**: `node vowel_counter.js 'Hello World'`

### Example 3: Bash Script (line_counter.sh)

- **Output Directory**: `./docker_output_bash`
- **Script**: Counts lines in input text
- **Example Usage**: `./line_counter.sh 'Line 1\nLine 2'`

### Example 4: Advanced Configuration

- **Output Directory**: `./docker_output_advanced`
- **Script**: Same as Example 1 but with custom settings
- **Features**: Lower budget limit, verbose output enabled
- **Budget Limit**: $0.10 (default)

## 🔧 Command Line Options

### Main Tool (`main.py`)

| Option            | Description                            | Default           |
| ----------------- | -------------------------------------- | ----------------- |
| `--api-key`       | OpenAI API key (required)              | -                 |
| `--script-path`   | Path to script to dockerize (required) | -                 |
| `--example-usage` | Example command for validation         | None              |
| `--output-dir`    | Output directory for generated files   | `./docker_output` |
| `--budget-limit`  | Maximum budget in USD                  | `0.10`            |
| `--verbose`       | Enable verbose output                  | False             |

### Example Runner (`example_usage.py`)

| Option            | Description           |
| ----------------- | --------------------- |
| `--api-key KEY`   | OpenAI API key        |
| `--run-example N` | Run example N (1-4)   |
| `--check`         | Check prerequisites   |
| `--verbose`       | Enable verbose output |
| `--help`          | Show help message     |

## 📁 Output Structure

After running any example, you'll find:

```
docker_output_[language]/
├── Dockerfile          # Generated Dockerfile
├── [script_file]       # Your original script (copied from source)
├── .dockerignore       # Auto-generated ignore rules
└── build_logs.txt      # Build and validation logs (if applicable)
```

**✅ Complete Build Context**: The output directory contains everything needed to build the Docker image manually. You can run `docker build .` directly in the output directory.

## 🧪 Testing Generated Images

After successful generation:

```bash
# Navigate to output directory
cd docker_output_python

# Build the Docker image
docker build -t my-script .

# Test with the example usage
docker run --rm my-script "Hello World"

# Interactive exploration
docker run --rm -it my-script bash
```

## 💡 Advanced Usage Patterns

### Custom Budget and Settings

```bash
python3 main.py \
  --api-key sk-your-key \
  --script-path ./my_script.py \
  --output-dir ./custom_output \
  --budget-limit 1.0 \
  --verbose
```

### Batch Processing Multiple Scripts

```bash
# Process multiple scripts with different output directories
for script in script1.py script2.js script3.sh; do
  python3 example_usage.py \
    --api-key sk-your-key \
    --script-path ./scripts/$script \
    --output-dir ./output_$script
done
```

### Environment Variable API Key

```bash
# Set API key in environment
export OPENAI_API_KEY=sk-your-key-here

# Tool will use environment variable if --api-key not provided
python3 main.py --script-path ./my_script.py
```

## 🔍 Troubleshooting

### Prerequisites Check

```bash
python3 example_usage.py --check
```

This will verify:

- ✅ Python version (3.8+)
- ✅ Dependencies installed
- ✅ Docker availability
- ✅ Sample scripts present
- ⚠️ API key configuration

### Common Issues

**Docker not available**

```bash
# Install Docker Desktop or Docker Engine
# Then verify: docker --version
```

**Missing dependencies**

```bash
pip3 install -r requirements.txt
```

**Script not found**

```bash
# Verify script path is correct
ls -la ../Jit-ai-challenge/
```

**API key issues**

```bash
# Test your API key
python3 -c "import openai; openai.api_key='sk-your-key'; print('Key valid')"
```

## 📊 Cost Management

The tool includes built-in budget tracking:

- **Default Budget**: $0.10 per run
- **Typical Costs**: $0.01-$0.50 per script
- **Cost Factors**: Script complexity, iterations needed
- **Tracking**: Real-time cost monitoring
- **Protection**: Automatic stop if budget exceeded

Example cost output:

```
💰 Total cost: $0.0234
📊 Budget: $0.0234/$0.10 (23.4% used)
```

## 🎯 Tips for Best Results

1. **Provide Example Usage**: Always include `--example-usage` for better validation
2. **Use Specific Output Dirs**: Each script should have its own output directory
3. **Start with Verbose**: Use `--verbose` flag to understand what's happening
4. **Check Prerequisites**: Run `--check` before your first attempt
5. **Budget Conservatively**: Start with lower budget limits for testing

## 🔄 Workflow Integration

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Generate Dockerfile
  run: |
    python3 main.py \
      --api-key ${{ secrets.OPENAI_API_KEY }} \
      --script-path ./app.py \
      --output-dir ./docker \
      --budget-limit 1.0
```

### Development Workflow

```bash
# 1. Develop your script
vim my_script.py

# 2. Generate Dockerfile
python3 example_usage.py --api-key $OPENAI_API_KEY --script-path ./my_script.py

# 3. Test the Docker image
cd docker_output && docker build -t my-app . && docker run my-app

# 4. Deploy or iterate
```

---

**Need help?** Run `python3 example_usage.py --help` for quick reference!
