# Repository Resource

Manage package repositories, system updates, and package manager operations.

## Overview

The Repository resource handles package manager lifecycle operations:

- Update package cache
- Upgrade installed packages
- Add and remove repositories
- Manage GPG keys
- Configure repository files

## Supported Package Managers

| Platform      | Package Manager | Update | Upgrade | Add Repo |
| ------------- | --------------- | ------ | ------- | -------- |
| Ubuntu/Debian | apt             | Yes    | Yes     | Yes      |
| Fedora/RHEL   | dnf             | Yes    | Yes     | Yes      |
| Arch Linux    | pacman          | Yes    | Yes     | Yes      |
| macOS         | brew            | Yes    | Yes     | Yes      |

## Basic Usage

### Update Package Cache

```python
from cook import Repository

Repository("apt-update", action="update")
```

Equivalent to:

```bash
apt-get update
```

### Upgrade All Packages

```python
Repository("apt-upgrade", action="upgrade")
```

Equivalent to:

```bash
apt-get upgrade -y
```

### Add Repository

```python
Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg",
    filename="docker.list"
)
```

## Actions

### update

Updates the package manager cache.

**Parameters:**

- `name`: Identifier for the resource

**Example:**

```python
Repository("system-update", action="update")
```

**Behavior:**

- APT: Runs `apt-get update`
- DNF: Runs `dnf check-update`
- Pacman: Runs `pacman -Sy`
- Brew: Runs `brew update`

**Idempotency:**

Checks cache age. If cache is fresh (less than 1 hour old), no action is taken.

### upgrade

Upgrades all installed packages.

**Parameters:**

- `name`: Identifier for the resource

**Example:**

```python
Repository("system-upgrade", action="upgrade")
```

**Behavior:**

- APT: Runs `apt-get upgrade -y`
- DNF: Runs `dnf upgrade -y`
- Pacman: Runs `pacman -Su --noconfirm`
- Brew: Runs `brew upgrade`

**Idempotency:**

Checks for upgradable packages. If none are available, no action is taken.

### add

Adds a new package repository.

**Parameters:**

- `name`: Repository identifier
- `repo`: Repository line (format varies by package manager)
- `key_url`: URL to GPG public key (optional)
- `key_id`: GPG key ID (optional)
- `key_server`: GPG keyserver (default: keyserver.ubuntu.com)
- `ppa`: Ubuntu PPA name (Ubuntu only)
- `tap`: Homebrew tap name (macOS only)
- `filename`: Custom filename for repository file
- `ensure`: "present" or "absent"

## Examples

### NodeSource Repository

Add Node.js 20.x repository:

```python
Repository(
    "nodesource",
    action="add",
    repo="deb https://deb.nodesource.com/node_20.x nodistro main",
    key_url="https://deb.nodesource.com/gpgkey/nodesource.gpg.key",
    filename="nodesource.list"
)
```

### Docker Repository

```python
Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg",
    filename="docker.list"
)
```

### Ubuntu PPA

```python
Repository(
    "ondrej-php",
    action="add",
    ppa="ppa:ondrej/php"
)
```

### Homebrew Tap

```python
Repository(
    "custom-tap",
    action="add",
    tap="homebrew/cask-fonts"
)
```

### Remove Repository

```python
Repository(
    "old-repo",
    action="add",
    repo="deb https://old.example.com/ubuntu focal main",
    ensure="absent"
)
```

## Complete Workflow

Typical pattern for adding a repository and installing packages:

```python
from cook import Repository, Package

# Update system
Repository("apt-update", action="update")
Repository("apt-upgrade", action="upgrade")

# Add Docker repository
Repository(
    "docker",
    action="add",
    repo="deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg",
    filename="docker.list"
)

# Update cache after adding repository
Repository("apt-update-post", action="update")

# Install packages from new repository
Package("docker", packages=[
    "docker-ce",
    "docker-ce-cli",
    "containerd.io",
])
```

## Variable Expansion

Repository lines support variable expansion:

```python
# $(lsb_release -cs) expands to Ubuntu codename
Repository(
    "example",
    repo="deb https://example.com/ubuntu $(lsb_release -cs) main"
)
```

On Ubuntu 22.04 (Jammy), this becomes:

```
deb https://example.com/ubuntu jammy main
```

## GPG Key Management

### From URL

```python
Repository(
    "repo-name",
    action="add",
    repo="deb https://example.com/ubuntu focal main",
    key_url="https://example.com/key.gpg"
)
```

Key is downloaded and stored in `/etc/apt/trusted.gpg.d/repo-name.gpg`

### From Keyserver

```python
Repository(
    "repo-name",
    action="add",
    repo="deb https://example.com/ubuntu focal main",
    key_id="9DC858229FC7DD38854AE2D88D81803C0EBFCD88",
    key_server="keyserver.ubuntu.com"
)
```

## Files Created

### APT (Debian/Ubuntu)

- Repository file: `/etc/apt/sources.list.d/{filename}`
- GPG key: `/etc/apt/trusted.gpg.d/{name}.gpg`

### DNF (Fedora/RHEL)

- Repository file: `/etc/yum.repos.d/{name}.repo`

### Pacman (Arch)

- Modifies: `/etc/pacman.conf`

## Security Considerations

### Non-Interactive Installation

All operations use non-interactive flags:

- APT: `DEBIAN_FRONTEND=noninteractive` + `-y`
- DNF: `-y`
- Pacman: `--noconfirm`

### GPG Key Verification

Always specify `key_url` or `key_id` when adding repositories from third parties:

```python
# Good: Includes GPG key
Repository(
    "docker",
    repo="deb https://download.docker.com/linux/ubuntu focal stable",
    key_url="https://download.docker.com/linux/ubuntu/gpg"
)

# Avoid: No GPG verification
Repository(
    "untrusted",
    repo="deb [trusted=yes] https://untrusted.example.com/repo focal main"
)
```

## Platform-Specific Notes

### APT Cache Age

Cache is considered stale if older than 1 hour. Modify by implementing custom check logic.

### DNF Update vs Check-Update

DNF uses `check-update` for the update action, which does not modify the system.

### Pacman Sync Database

Pacman's `-Sy` only synchronizes package databases, does not upgrade packages.

### Homebrew Taps

Homebrew taps are Git repositories. Removing a tap does not uninstall packages from that tap.

## API Reference

See [cook/resources/repository.py](https://github.com/gleicon/cook/blob/main/cook/resources/repository.py) for complete source code and docstrings.
