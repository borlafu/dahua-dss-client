# Contributing to Dahua DSS Client

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/borlafu/dahua-dss-client/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Error messages or logs

### Suggesting Features

1. Check existing [Issues](https://github.com/borlafu/dahua-dss-client/issues) and [Discussions](https://github.com/borlafu/dahua-dss-client/discussions)
2. Create a new issue or discussion with:
   - Clear description of the feature
   - Use case and benefits
   - Proposed implementation (if applicable)

### Pull Requests

1. **Fork the repository**

   ```bash
   git clone https://github.com/borlafu/dahua-dss-client.git
   cd dahua-dss-client
   ```

2. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set up development environment**

   ```bash
   poetry install
   poetry shell
   ```

4. **Make your changes**

   - Write clear, concise code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

5. **Run tests and linting**

   ```bash
   poetry run pytest
   poetry run black dahua_dss tests
   poetry run isort dahua_dss tests
   poetry run mypy dahua_dss
   ```

6. **Commit your changes**

   ```bash
   git add .
   git commit -m "Add feature: clear description"
   ```

7. **Push to your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use type hints for function signatures
- Maximum line length: 120 characters
- Use Black for formatting
- Use isort for import sorting

```bash
# Format code
poetry run black dahua_dss tests

# Sort imports
poetry run isort dahua_dss tests

# Type checking
poetry run mypy dahua_dss
```

### Testing

- Write unit tests for all new features
- Maintain or improve code coverage
- Use pytest for testing
- Mock external API calls

```bash
# Run tests with coverage
poetry run pytest

# Run specific test file
poetry run pytest tests/test_client.py -v
```

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions and classes
- Include code examples

### Commit Messages

Follow conventional commits format:

```
type(scope): brief description

Detailed description (optional)

Fixes #issue_number
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:

```
feat(client): add support for HTTPS connections
fix(auth): handle token expiration correctly
docs(readme): update installation instructions
```

## Project Structure

```
dahua-dss-client/
├── dahua_dss/          # Main package
│   ├── __init__.py
│   ├── client.py       # API client
│   └── cli.py          # CLI interface
└── tests/              # Test files
```

## Setting Up Development Environment

### Prerequisites

- Python 3.13+
- Poetry
- Git
- Docker (optional)

### Installation

```bash
# Clone your fork
git clone https://github.com/borlafu/dahua-dss-client.git
cd dahua-dss-client

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run tests
poetry run pytest
```

## Code Review Process

1. All PRs require at least one review
2. CI/CD pipeline must pass
3. Code coverage should not decrease
4. Documentation must be updated
5. Maintainer will review and provide feedback
6. Address review comments
7. Once approved, PR will be merged

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. After merge, maintainer creates GitHub release
5. CI/CD automatically publishes to PyPI

## Getting Help

- 📖 Read the [documentation](README.md)
- 💬 Ask in [Discussions](https://github.com/borlafu/dahua-dss-client/discussions)
- 🐛 Report bugs in [Issues](https://github.com/borlafu/dahua-dss-client/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in the README.md and release notes.

Thank you for contributing! 🎉
