# Cook

Configuration management in Python for the Impatient.

## Overview

Cook is a Python-based configuration management tool designed for simplicity and practicality. It provides a declarative way to manage server configurations without the complexity of enterprise frameworks.

## Key Features

- **Pure Python Configuration**: No YAML or custom DSL required
- **Drift Detection**: Automatic detection and correction of configuration drift
- **Recording Mode**: Learn from manual changes and generate code
- **SSH Transport**: Local or remote execution with sudo support
- **MCP Server Integration**: AI-assisted infrastructure management
- **Cross-Platform**: Works on Linux and macOS

## Core Resources

Cook provides fundamental building blocks for system configuration:

- **File**: Manage files, directories, and templates (Jinja2)
- **Package**: Install and manage system packages (apt, dnf, pacman, brew)
- **Repository**: Manage package repositories and system updates
- **Service**: Control systemd and launchctl services
- **Exec**: Execute commands with idempotency guards

## Quick Example

```python
from cook import File, Package, Service

Package("nginx")

File("/etc/nginx/nginx.conf",
     content="""
     events { worker_connections 1024; }
     http {
         server {
             listen 80;
             location / { return 200 'Hello'; }
         }
     }
     """,
     mode=0o644)

Service("nginx", running=True, enabled=True)
```

```bash
cook plan server.py
cook apply server.py
```

## Use Cases

Cook is designed for:

- VM provisioning and configuration
- Container image builds
- Local development environment setup
- Server fleet management
- Migration from cloud to physical servers
- Infrastructure as code without enterprise overhead

## Philosophy

Cook fills the gap between shell scripts and enterprise configuration management. It provides:

- **Testability**: Pure Python enables unit and integration testing
- **Observability**: Clear logging and state tracking
- **Simplicity**: Direct mapping from desired state to implementation
- **Integration**: Python ecosystem enables easy customization

## Project Status

Cook is in beta with all core features implemented. Production use requires careful testing in your specific environment.

## Next Steps

- [Installation Guide](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [Core Concepts](getting-started/concepts.md)
- [Resource Reference](resources/index.md)
