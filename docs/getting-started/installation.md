# Installation

## Requirements

- Python 3.8 or higher
- Linux or macOS operating system
- pip or uv package manager

## Using uv (Recommended)

uv is a fast Python package installer and resolver.

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/gleicon/cook
cd cook

# Create virtual environment and install
uv venv
uv pip install -e ".[all]"
source .venv/bin/activate
```

## Using pip

```bash
# Clone repository
git clone https://github.com/gleicon/cook
cd cook

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with all features
pip install -e ".[all]"
```

## Install Options

Cook has optional feature sets:

### Minimal Installation

Core functionality only:

```bash
pip install -e .
```

### Specific Features

Install only what you need:

```bash
# Templates support (Jinja2)
pip install -e ".[templates]"

# SSH remote execution
pip install -e ".[ssh]"

# State persistence
pip install -e ".[state]"

# Recording mode
pip install -e ".[record]"

# All features
pip install -e ".[all]"
```

### Development Installation

For development and testing:

```bash
pip install -e ".[all,dev,docs]"
```

## Verify Installation

```bash
cook --version
```

Expected output:

```
cook, version 0.1.0
```

## Platform-Specific Notes

### Ubuntu/Debian

Some features require system packages:

```bash
sudo apt-get install python3-dev libsqlite3-dev
```

### macOS

Homebrew Python is recommended:

```bash
brew install python@3.11
```

### Arch Linux

```bash
sudo pacman -S python python-pip
```

## See also

- [Quick Start Guide](quickstart.md)
- [Core Concepts](concepts.md)
