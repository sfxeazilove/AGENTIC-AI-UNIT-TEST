# AutoCover 🤖

An intelligent, agentic AI unit testing framework that automatically generates, executes, and maintains comprehensive test suites for your codebase using LangGraph pipeline orchestration.

## 🚀 Overview

AutoCover revolutionizes unit testing by leveraging Large Language Models (LLMs) and intelligent agents to understand your project structure, generate meaningful tests, execute them, and continuously improve test coverage through an iterative feedback loop.

### Key Features

- **🧠 Intelligent Code Analysis**: Automatically understands project structure and dependencies
- **📝 AI-Powered Test Generation**: Uses LLMs to author contextually relevant unit tests
- **🔄 Automated Test Execution**: Builds and runs tests with comprehensive reporting
- **🛠️ Self-Healing Tests**: Automatically fixes test failures and compilation errors
- **♻️ Continuous Improvement**: Refactors tests based on execution results and feedback
- **✅ Quality Validation**: Ensures code style, assertions, and best practices compliance
- **🔗 LangGraph Integration**: Orchestrates the entire pipeline with state management

## 🏗️ Architecture

AutoCover follows a sophisticated pipeline architecture with six core components:

```
Scaffolder → Generator → Executor → Fixer
     ↓           ↓         ↓        ↑
     └─────→ Refactor ←────┘        │
                ↓                   │
            Validator ──────────────┘
```

### Pipeline Components

1. **Scaffolder**: Analyzes project structure, identifies test targets, and prepares the testing environment
2. **Generator**: Employs LLMs to author intelligent, context-aware unit tests
3. **Executor**: Builds and executes test suites with detailed reporting
4. **Fixer**: Automatically resolves test failures and compilation issues
5. **Refactor**: Optimizes tests based on execution results and coverage analysis
6. **Validator**: Ensures code quality, style compliance, and assertion effectiveness

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+ (for JavaScript/TypeScript projects)
- Git
- Docker (optional, for containerized testing)

## 🔧 Installation

### From PyPI
```bash
pip install autocover
```

### From Source
```bash
git clone https://github.com/yourusername/autocover.git
cd autocover
pip install -e .
```

### With Development Dependencies
```bash
git clone https://github.com/yourusername/autocover.git
cd autocover
pip install -e ".[dev]"
```

## ⚙️ Configuration

Create an `autocover.yaml` configuration file in your project root:

```yaml
# autocover.yaml
project:
  name: "my-awesome-project"
  language: "python"  # python, javascript, typescript, java, etc.
  source_dirs: ["src", "lib"]
  test_dir: "tests"
  exclude_patterns: ["*.pyc", "__pycache__", "node_modules"]

llm:
  provider: "openai"  # openai, anthropic, cohere, local
  model: "gpt-4"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.2
  max_tokens: 2048

testing:
  framework: "pytest"  # pytest, jest, junit, etc.
  coverage_threshold: 80
  max_iterations: 3
  timeout: 300

pipeline:
  enable_parallel: true
  max_workers: 4
  retry_attempts: 2
  
validation:
  style_guide: "pep8"  # pep8, airbnb, google, etc.
  enforce_docstrings: true
  assertion_strength: "medium"  # low, medium, high
```

## 🚀 Quick Start

### Basic Usage

```bash
# Initialize AutoCover in your project
autocover init

# Generate and run tests for entire project
autocover run

# Generate tests for specific files
autocover run --files src/utils.py src/models.py

# Run with custom configuration
autocover run --config custom-config.yaml

# Generate tests with higher coverage threshold
autocover run --coverage 95
```

### Programmatic Usage

```python
from autocover import AutoCover, Config

# Initialize with custom configuration
config = Config(
    project_name="my-project",
    language="python",
    source_dirs=["src"],
    llm_provider="openai",
    llm_model="gpt-4"
)

# Create AutoCover instance
auto_cover = AutoCover(config)

# Run the complete pipeline
results = auto_cover.run()

print(f"Coverage: {results.coverage_percentage}%")
print(f"Tests Generated: {results.tests_generated}")
print(f"Tests Passed: {results.tests_passed}")
```

## 📊 Pipeline Workflow

### 1. Scaffolder Phase
- Scans project structure and identifies source files
- Analyzes dependencies and imports
- Creates test file templates and directory structure
- Generates testing metadata and context

### 2. Generator Phase
- Uses LLM to understand code functionality
- Generates comprehensive unit tests with multiple scenarios
- Creates edge case tests and error handling tests
- Ensures proper mocking and test isolation

### 3. Executor Phase
- Compiles and executes generated tests
- Collects coverage metrics and performance data
- Generates detailed execution reports
- Identifies failing tests and error patterns

### 4. Fixer Phase
- Analyzes test failures and compilation errors
- Automatically fixes common issues (imports, syntax, logic)
- Resolves dependency conflicts
- Updates test configurations if needed

### 5. Refactor Phase
- Optimizes test structure and organization
- Removes redundant tests and improves efficiency
- Enhances test readability and maintainability
- Updates assertions based on execution feedback

### 6. Validator Phase
- Validates code style and formatting
- Ensures proper assertion usage
- Checks test coverage completeness
- Generates final quality report

## 🔄 Advanced Features

### Custom Test Templates

```python
# custom_templates.py
from autocover.templates import TestTemplate

class CustomAPITestTemplate(TestTemplate):
    def generate_test_class(self, target_class):
        return f"""
import pytest
from unittest.mock import Mock, patch
from {target_class.module} import {target_class.name}

class Test{target_class.name}:
    def setup_method(self):
        self.instance = {target_class.name}()
    
    # Custom test methods generated here
    """

# Register custom template
auto_cover.register_template("api", CustomAPITestTemplate())
```

### Pipeline Customization

```python
from autocover.pipeline import Pipeline
from autocover.agents import CustomFixerAgent

# Create custom pipeline
pipeline = Pipeline()
pipeline.add_agent("custom_fixer", CustomFixerAgent())
pipeline.set_retry_policy(max_attempts=5, backoff_factor=2)

auto_cover = AutoCover(config, pipeline=pipeline)
```

### Integration with CI/CD

```yaml
# .github/workflows/autocover.yml
name: AutoCover CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install AutoCover
      run: pip install autocover
    
    - name: Run AutoCover
      run: autocover run --coverage 85 --output coverage-report.json
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    
    - name: Upload Coverage
      uses: codecov/codecov-action@v3
      with:
        file: coverage-report.json
```

## 📈 Monitoring and Reporting

### Coverage Reports

```bash
# Generate HTML coverage report
autocover run --report html

# Generate JSON report for CI integration
autocover run --report json --output coverage.json

# Generate detailed analysis report
autocover run --report detailed --include-metrics
```

### Dashboard Integration

```python
from autocover.dashboard import Dashboard

# Launch web dashboard
dashboard = Dashboard(auto_cover)
dashboard.serve(host="0.0.0.0", port=8080)
```

## 🛠️ Troubleshooting

### Common Issues

**LLM API Rate Limits**
```bash
# Use local model or reduce concurrency
autocover run --max-workers 1 --llm-provider local
```

**Test Generation Failures**
```bash
# Enable debug mode
autocover run --debug --verbose

# Use simpler model for complex codebases
autocover run --llm-model gpt-3.5-turbo
```

**Compilation Errors**
```bash
# Skip compilation checks
autocover run --skip-compilation

# Use specific language version
autocover run --python-version 3.9
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/yourusername/autocover.git
cd autocover
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=autocover tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for pipeline orchestration
- [OpenAI](https://openai.com) for LLM capabilities
- [Anthropic](https://anthropic.com) for Claude integration
- The open-source testing community

## 📚 Documentation

- [User Guide](docs/user-guide.md)
- [API Reference](docs/api-reference.md)
- [Pipeline Architecture](docs/architecture.md)
- [Configuration Reference](docs/configuration.md)
- [Examples](examples/)

## 🔗 Links

- [GitHub Repository](https://github.com/yourusername/autocover)
- [Documentation](https://autocover.readthedocs.io)
- [PyPI Package](https://pypi.org/project/autocover)
- [Discord Community](https://discord.gg/autocover)

---

**AutoCover** - Intelligent AI-powered unit testing for the modern developer. Built with ❤️ by the AutoCover team.