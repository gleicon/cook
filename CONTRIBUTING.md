# Contributing to Cook

Thank you for your interest in contributing to Cook! 🍳

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Adding New Resources](#adding-new-resources)
- [Documentation](#documentation)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment
- Report unacceptable behavior to maintainers

## Getting Started

### Prerequisites

- Python 3.8 or higher
- uv (recommended) or pip
- Git
- Basic understanding of configuration management

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/cook-py.git
cd cook-py

# Set up development environment with uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Or with pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify installation
cook --help
```

## Project Structure

```
cook-py/
├── cook/
│   ├── __init__.py          # Package exports
│   ├── cli/
│   │   └── main.py          # CLI commands (Click)
│   ├── core/
│   │   ├── resource.py      # Base Resource class
│   │   └── executor.py      # Plan/Apply engine
│   ├── resources/
│   │   ├── file.py          # File resource
│   │   ├── pkg.py           # Package resource
│   │   ├── service.py       # Service resource
│   │   └── exec.py          # Exec resource
│   ├── transport/           # SSH/local transport (planned)
│   ├── state/               # State persistence (planned)
│   ├── monitor/             # Drift monitoring (planned)
│   └── sandbox/             # Sandbox execution (planned)
├── tests/                   # Test suite
├── examples/                # Example configs
├── docs/                    # Documentation
└── pyproject.toml          # Project config
```

## Making Changes

### Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes
4. **Test** your changes
5. **Commit** with clear messages
6. **Push** to your fork
7. **Open** a Pull Request

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

Examples:
- `feature/drift-monitoring`
- `fix/pkg-resource-debian`
- `docs/ssh-transport-guide`

### Commit Messages

Follow conventional commits:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat(resources): add Docker resource
fix(pkg): handle missing package manager
docs(README): update installation instructions
refactor(executor): simplify reload trigger logic
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cook --cov-report=html

# Run specific test file
pytest tests/test_file.py

# Run specific test
pytest tests/test_file.py::test_file_creation
```

### Writing Tests

```python
# tests/test_file.py
import pytest
from cook import File
from cook.core.executor import reset_executor
from cook.core.resource import Platform

def test_file_creation():
    """Test file resource creation."""
    reset_executor()

    f = File("/tmp/test.txt", content="Hello")

    assert f.id == "file:/tmp/test.txt"
    assert f.resource_type() == "file"

def test_file_plan():
    """Test file resource planning."""
    reset_executor()
    platform = Platform.detect()

    f = File("/tmp/test.txt", content="Hello")
    plan = f.plan(platform)

    assert plan.action in [Action.CREATE, Action.NONE]
```

### Test Coverage Goals

- Aim for 80%+ code coverage
- All new features must have tests
- Bug fixes should include regression tests

## Code Style

### Python Style Guide

We follow PEP 8 with some modifications:

```bash
# Format code with Black
black cook/

# Check types with mypy
mypy cook/

# Lint with flake8 (if configured)
flake8 cook/
```

### Style Guidelines

**Use type hints:**
```python
# Good
def plan(self, platform: Platform) -> Plan:
    ...

# Avoid
def plan(self, platform):
    ...
```

**Use docstrings:**
```python
def check(self, platform: Platform) -> Dict[str, Any]:
    """
    Check current state of the resource.

    Args:
        platform: Platform information

    Returns:
        Dictionary of current state properties
    """
    ...
```

**Prefer list comprehensions:**
```python
# Good
files = [f for f in resources if isinstance(f, File)]

# Avoid
files = []
for f in resources:
    if isinstance(f, File):
        files.append(f)
```

**Use f-strings:**
```python
# Good
print(f"Resource: {resource.id}")

# Avoid
print("Resource: " + resource.id)
print("Resource: {}".format(resource.id))
```

### Security Guidelines

**Always use list arguments for subprocess:**
```python
# Good
subprocess.run(["apt-get", "install", "-y", "nginx"])

# Bad
subprocess.run("apt-get install -y nginx", shell=True)
```

**Validate user input:**
```python
# Good
if not re.match(r'^[a-z0-9-]+$', name):
    raise ValueError("Invalid name")

# Bad
File(f"/var/www/{user_input}")  # Injection risk!
```

See [SECURITY.md](SECURITY.md) for more details.

## Submitting Changes

### Pull Request Process

1. **Update documentation** - README, docstrings, etc.
2. **Add tests** - Ensure new code is tested
3. **Run tests** - All tests must pass
4. **Update CHANGELOG** - Add entry for your change
5. **Open PR** - Use clear title and description

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No security issues introduced
```

### Review Process

- Maintainers will review within 48-72 hours
- Address feedback in new commits
- Once approved, maintainer will merge

## Adding New Resources

### Resource Template

```python
"""
[Resource] resource - [brief description].

Handles:
- [Feature 1]
- [Feature 2]
"""

from typing import Dict, Any, Optional
from cook.core.resource import Resource, Plan, Action, Platform
from cook.core.executor import get_executor

class [Resource](Resource):
    """
    [Resource] resource for [purpose].

    Examples:
        [Resource]([args])
    """

    def __init__(self, name: str, **options):
        super().__init__(name, **options)
        # Auto-register
        get_executor().add(self)

    def resource_type(self) -> str:
        return "[type]"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check current state."""
        # Implement state checking
        return {"exists": False}

    def desired_state(self) -> Dict[str, Any]:
        """Return desired state."""
        # Implement desired state
        return {"exists": True}

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Apply changes."""
        # Implement apply logic
        pass
```

### Resource Checklist

- [ ] Inherits from `Resource`
- [ ] Implements all abstract methods
- [ ] Auto-registers with executor
- [ ] Has comprehensive docstring
- [ ] Handles errors gracefully
- [ ] Platform-aware (Linux/macOS)
- [ ] Has examples
- [ ] Has tests
- [ ] Documented in README

## Documentation

### Documentation Types

1. **Code comments** - Explain *why*, not *what*
2. **Docstrings** - Describe API and usage
3. **README** - Quick start and overview
4. **Examples** - Practical use cases
5. **Guides** - In-depth tutorials

### Documentation Standards

**Module docstrings:**
```python
"""
Module for [purpose].

This module provides [functionality].

Example:
    from cook.[module] import [Class]

    [example usage]
"""
```

**Function docstrings:**
```python
def function(arg1: str, arg2: int) -> bool:
    """
    Brief description.

    Longer description if needed.

    Args:
        arg1: Description of arg1
        arg2: Description of arg2

    Returns:
        Description of return value

    Raises:
        ValueError: When validation fails

    Example:
        >>> function("test", 42)
        True
    """
```

## Getting Help

- **Questions:** Open a GitHub Discussion
- **Bugs:** Open a GitHub Issue
- **Security:** See [SECURITY.md](SECURITY.md)
- **Chat:** [Link to Discord/Slack if available]

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Eligible for maintainer role (active contributors)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Cook!** 🍳
