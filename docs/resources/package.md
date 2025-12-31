# Package Resource

Install and manage system packages across multiple platforms.

## Overview

The Package resource handles package installation and removal:

- Install packages on apt, dnf, pacman, and brew
- Remove packages
- Check package installation status
- Support for single and multiple packages
- Automatic platform detection
- Non-interactive installation (no confirmation prompts)

## Supported Package Managers

| Platform      | Package Manager | Install | Remove | Check |
| ------------- | --------------- | ------- | ------ | ----- |
| Ubuntu/Debian | apt             | Yes     | Yes    | Yes   |
| Fedora/RHEL   | dnf             | Yes     | Yes    | Yes   |
| Arch Linux    | pacman          | Yes     | Yes    | Yes   |
| macOS         | brew            | Yes     | Yes    | Yes   |

## Basic Usage

### Single Package

```python
from cook import Package

Package("nginx")
```

### Multiple Packages (List)

```python
Package(["gcc", "make", "autoconf"])
```

### Multiple Packages (Named Group)

```python
Package("build-tools", packages=["gcc", "make", "autoconf"])
```

### Remove Package

```python
Package("apache2", ensure="absent")
```

## Parameters

### name

**Required**. Package name or list of packages.

Can be:
- **String**: Single package name
- **List**: Multiple package names (convenience syntax)

```python
# Single package
Package("nginx")

# Multiple packages
Package(["nginx", "curl", "git"])
```

### packages

List of package names to install as a group.

```python
Package("web-server", packages=["nginx", "certbot", "python3-certbot-nginx"])
```

### ensure

Package state: `"present"`, `"absent"`, or `"latest"`.

**Default:** `"present"`

```python
# Install package
Package("nginx", ensure="present")

# Remove package
Package("apache2", ensure="absent")

# Upgrade to latest
Package("nginx", ensure="latest")
```

### version

Specific package version to install (support varies by package manager).

```python
Package("nginx", version="1.18.0-1ubuntu1")
```

**Note:** Version support depends on the package manager. Some package managers may not support pinning to specific versions.

## Examples

### Web Server Stack

```python
from cook import Package

# Individual packages
Package("nginx")
Package("certbot")

# Or as a group
Package("web-stack", packages=[
    "nginx",
    "certbot",
    "python3-certbot-nginx"
])
```

### Development Tools

```python
Package("build-tools", packages=[
    "gcc",
    "g++",
    "make",
    "autoconf",
    "automake",
    "cmake"
])
```

### Database Server

```python
Package("postgresql", packages=[
    "postgresql",
    "postgresql-contrib",
    "libpq-dev"
])
```

### Node.js Application Dependencies

```python
# After adding NodeSource repository
Package("nodejs")

# Additional tools
Package("node-tools", packages=[
    "npm",
    "yarn"
])
```

### Docker Installation

```python
# After adding Docker repository
Package("docker", packages=[
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
    "docker-compose-plugin"
])
```

### Remove Unwanted Packages

```python
Package("apache2", ensure="absent")
Package("sendmail", ensure="absent")
```

## Non-Interactive Installation

All package installations run non-interactively to prevent blocking on user input.

### APT (Debian/Ubuntu)

```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y <packages>
```

Prevents configuration prompts and package installation questions.

### DNF (Fedora/RHEL)

```bash
dnf install -y <packages>
```

The `-y` flag automatically confirms all prompts.

### Pacman (Arch)

```bash
pacman -S --noconfirm <packages>
```

The `--noconfirm` flag bypasses all confirmation prompts.

### Brew (macOS)

```bash
brew install <packages>
```

Homebrew does not prompt for confirmation by default.

## Package Groups

Group related packages for better organization:

```python
from cook import Package

# Web server stack
Package("web-server", packages=[
    "nginx",
    "certbot",
    "python3-certbot-nginx"
])

# Application runtime
Package("app-runtime", packages=[
    "python3",
    "python3-pip",
    "python3-venv"
])

# Monitoring tools
Package("monitoring", packages=[
    "prometheus-node-exporter",
    "netdata"
])
```

## Idempotency

Package resources are idempotent. Repeated installation of the same package does not reinstall.

```python
Package("nginx")
# First run: Installs nginx
# Second run: Detects nginx already installed, no changes
```

Package removal:

```python
Package("apache2", ensure="absent")
# First run: Removes apache2
# Second run: Detects apache2 not installed, no changes
```

## Platform-Specific Behavior

### APT (Debian/Ubuntu)

```python
Package("nginx")
```

Equivalent to:

```bash
apt-get install -y nginx
```

Package check uses `dpkg-query`:

```bash
dpkg-query -W -f='${Version}' nginx
```

### DNF (Fedora/RHEL)

```python
Package("nginx")
```

Equivalent to:

```bash
dnf install -y nginx
```

Package check uses `rpm`:

```bash
rpm -q --queryformat '%{VERSION}' nginx
```

### Pacman (Arch)

```python
Package("nginx")
```

Equivalent to:

```bash
pacman -S --noconfirm nginx
```

Package check:

```bash
pacman -Q nginx
```

### Homebrew (macOS)

```python
Package("nginx")
```

Equivalent to:

```bash
brew install nginx
```

Package check:

```bash
brew list --versions nginx
```

## Complete Workflow

Typical pattern for system setup:

```python
from cook import Repository, Package

# Update package cache
Repository("apt-update", action="update")

# Upgrade existing packages
Repository("apt-upgrade", action="upgrade")

# Install system tools
Package("system-tools", packages=[
    "curl",
    "wget",
    "git",
    "vim",
    "htop"
])

# Install web server
Package("nginx")

# Install application runtime
Package("python-runtime", packages=[
    "python3",
    "python3-pip",
    "python3-venv"
])
```

## Working with Repositories

Add custom repositories before installing packages from them:

```python
from cook import Repository, Package

# Add NodeSource repository
Repository(
    "nodesource",
    action="add",
    repo="deb https://deb.nodesource.com/node_20.x nodistro main",
    key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key"
)

# Update cache after adding repository
Repository("apt-update", action="update")

# Install from new repository
Package("nodejs")
```

## Version Management

Request specific versions when needed:

```python
# Specific version
Package("nginx", version="1.18.0-1ubuntu1")

# Latest version
Package("nginx", ensure="latest")
```

**Note:** Version support varies by package manager. Test on your target platform.

## Security Considerations

### Package Sources

Only install packages from trusted repositories:

```python
# Good: Official repository
Package("nginx")

# Good: Well-known third-party with GPG verification
Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg"
)
Package("docker-ce")
```

### System Updates

Keep systems updated:

```python
from cook import Repository, Package

# Regular updates
Repository("system-update", action="update")
Repository("system-upgrade", action="upgrade")
```

### Minimal Installation

Install only necessary packages:

```python
# Install minimal set
Package("production-tools", packages=[
    "nginx",
    "python3",
    "certbot"
])

# Avoid installing development tools on production unless needed
```

## Common Patterns

### Full LEMP Stack

```python
from cook import Repository, Package

# Update system
Repository("apt-update", action="update")

# Install LEMP stack
Package("lemp", packages=[
    "nginx",
    "mysql-server",
    "php-fpm",
    "php-mysql"
])
```

### Python Development Environment

```python
Package("python-dev", packages=[
    "python3",
    "python3-pip",
    "python3-venv",
    "python3-dev",
    "build-essential"
])
```

### Container Platform

```python
# Add Docker repository first
Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg"
)

Repository("apt-update", action="update")

# Install Docker
Package("docker", packages=[
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
    "docker-compose-plugin"
])
```

### SSL/TLS Certificates

```python
Package("certbot", packages=[
    "certbot",
    "python3-certbot-nginx"
])
```

## Troubleshooting

### Package Not Found

Ensure repository is added and cache is updated:

```python
# Add repository
Repository("custom-repo", action="add", repo="...")

# Update cache
Repository("apt-update", action="update")

# Then install
Package("custom-package")
```

### Installation Fails

Check platform compatibility and package name:

```python
# Ubuntu/Debian
Package("nodejs")

# Some platforms may use different names
# Verify with: apt-cache search nodejs
```

### Version Conflicts

Use version pinning when specific versions are required:

```python
Package("nginx", version="1.18.0-1ubuntu1")
```

## API Reference

See [cook/resources/pkg.py](https://github.com/gleicon/cook/blob/main/cook/resources/pkg.py) for complete source code and implementation details.
