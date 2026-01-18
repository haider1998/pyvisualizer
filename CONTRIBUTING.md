# Contributing to PyVisualizer

Thank you for your interest in contributing to PyVisualizer! This document provides guidelines and information for contributors.

## 🚀 Quick Start

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/PyVisualizer.git
   cd PyVisualizer
   ```

2. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   make install-dev
   ```

3. **Run Tests**
   ```bash
   make test
   ```

## 📁 Project Structure

```
pyvisualizer/
├── pyvisualizer/          # Main package
│   ├── __init__.py        # Package exports
│   ├── cli.py             # Command-line interface
│   ├── core/              # Core analysis modules
│   │   ├── analyzer.py    # AST analysis
│   │   ├── graph.py       # Call graph construction
│   │   └── resolver.py    # Function resolution
│   ├── visualizers/       # Output generators
│   │   ├── mermaid.py     # Mermaid diagrams
│   │   └── d3.py          # D3.js interactive HTML
│   └── utils/             # Utilities
│       └── file_discovery.py
├── tests/                 # Test suite
├── examples/              # Example projects
├── docs/                  # Documentation
└── .github/workflows/     # CI/CD pipelines
```

## 🔧 Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Install package in editable mode |
| `make install-dev` | Install with development dependencies |
| `make test` | Run test suite |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Run linters (flake8, mypy) |
| `make format` | Format code with black and isort |
| `make docs` | Generate architecture diagrams |
| `make clean` | Remove build artifacts |

## 🧪 Testing

We use pytest for testing. Please ensure:

- All new features have corresponding tests
- Tests are placed in the `tests/` directory
- Test files follow the pattern `test_*.py`
- Test functions follow the pattern `test_*`

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_analyzer.py -v

# Run with coverage
make test-cov
```

## 📝 Code Style

We follow PEP 8 guidelines with the following tooling:

- **Black** - Code formatting (line length: 100)
- **isort** - Import sorting (configured for Black compatibility)
- **flake8** - Linting
- **mypy** - Type checking

Before submitting a PR, please run:

```bash
make format  # Auto-format code
make lint    # Check for issues
```

## 🔀 Pull Request Process

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Write clear, concise commit messages
   - Add tests for new functionality
   - Update documentation as needed

3. **Run Quality Checks**
   ```bash
   make format
   make lint
   make test
   ```

4. **Submit Your PR**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure CI checks pass

## 📜 Commit Message Guidelines

Follow conventional commits format:

```
type(scope): short description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

Example:
```
feat(visualizers): add support for Graphviz DOT format

- Added new graphviz.py visualizer module
- Updated CLI to support 'dot' format option
- Added tests for DOT output generation

Closes #42
```

## 🐛 Reporting Issues

When reporting bugs, please include:

1. Python version (`python --version`)
2. PyVisualizer version (`py-code-visualizer --version`)
3. Operating system
4. Steps to reproduce
5. Expected vs actual behavior
6. Sample code (if applicable)

## 💡 Feature Requests

Feature requests are welcome! Please:

1. Check if the feature is already requested
2. Provide a clear use case
3. Consider implementation complexity
4. Be open to discussion

## 🏷️ Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

## 📄 License

By contributing to PyVisualizer, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Your contributions make PyVisualizer better for everyone. We appreciate your time and effort!
