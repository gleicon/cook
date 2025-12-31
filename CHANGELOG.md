# Changelog

## [Unreleased]

### Fixed

- **Resource redefinition support**: Fixed duplicate resource error when the same resource path is defined multiple times
  - Executor now implements "last definition wins" semantics
  - Enables multi-phase configurations (e.g., HTTP → HTTPS nginx config)
  - Maintains execution order when resources are replaced
  - Added comprehensive unit tests in `tests/unit/test_executor.py`
  - See `examples/minimidia/minimidia.py` for real-world usage

### Added

- SSH transport layer (Paramiko-based) 
  - LocalTransport for local execution
  - SSHTransport for remote deployment
  - CLI flags: --host, --user, --key, --port
  - File transfer via SFTP
  - Context manager support
- State persistence (SQLite) 
  - Resource state tracking in ~/.cook/state.db
  - Change history with who/when/what
  - CLI commands: state list, show, history, drift
  - Auto-enabled during apply
  - Context manager support
- Drift monitoring (completed)
  - Detect configuration drift via check-drift command
  - Compare current vs stored state
  - Mark drifted resources in state db
  - DriftDetector class with context manager
  - Integration with state persistence
- Code cleanup
  - Removed emojis from all example files
  - Removed emojis from print statements and documentation
  - Terse, technical output style
- Recording mode (completed)
  - PTY-based terminal recorder
  - Filesystem watcher using watchdog library
  - Command parser for common patterns (apt, systemctl, mkdir, etc.)
  - Python code generator from captured events
  - CLI commands: record start, record generate
  - JSON storage for recording sessions
  - Captures both commands and file changes
- Testing infrastructure (completed)
  - Comprehensive test plan (TEST_PLAN.md)
  - Unit tests with pytest (19 tests)
  - Integration tests for full workflows (6 tests)
  - Cross-platform VM testing (Vagrant + Lima)
  - Python-based test runner (works on macOS & Linux)
  - Automated test runner scripts
  - pytest configuration with markers
  - CI-ready test structure
- MCP server for AI integration (completed)
  - JSON-RPC 2.0 server over stdio
  - 7 tools for Cook operations
  - Config generation from natural language
  - Plan/apply operations
  - State queries and drift detection
  - Recording integration
  - Claude Desktop integration
  - Comprehensive documentation (MCP_SERVER.md)

## [0.1.0] - 2024-12-27

### Added

- Initial Python port from Lathe (Go + Starlark)
- Core resource pattern (Check/Plan/Apply)
- Resource types:
  - **File** - Files, directories, permissions, Jinja2 templates
  - **Package** - apt, dnf, pacman, brew support
  - **Service** - systemd, launchctl with reload/restart triggers
  - **Exec** - Command execution with idempotency guards
- CLI commands:
  - `cook plan` - Show planned changes
  - `cook apply` - Apply configuration
  - `cook version` - Show version
- Service reload triggers (reload_on, restart_on)
- Platform detection (Linux, macOS, distros)
- Global resource registry
- Development setup with uv
- Examples:
  - Simple file example
  - Nginx reload example
  - Web server example
- Documentation:
  - README.md
  - SECURITY.md
  - CONTRIBUTING.md
  - COMPARISON.md (Lathe vs Cook)
  - PYTHON-PORT-STATUS.md

### Security

- Fixed subprocess security issues
  - Package resource uses list arguments (no shell=True)
  - Service resource uses list arguments
  - Exec resource documented shell=True security implications
- Added comprehensive SECURITY.md

### Changed

- Project renamed from Lathe to Cook
- Moved from Go + Starlark to pure Python
- Simplified codebase (1,200 lines vs 3,200 lines)
- Using Jinja2 for templates instead of Go templates
- Using Click for CLI instead of custom arg parsing

## Project History

### Why the Rewrite?

Cook was based on **Lathe**, a Go + Starlark PaaS and config automation that was successful but had limitations:

- Starlark is a Python subset - limited features
- No try/except, with/as, external libraries
- Cross-compilation issues with CGO (SQLite)
- ResourceRef wrapper needed for resource references
- Harder to extend and contribute to

**Cook** (Pure Python) went straight to Python:

- Benefits of the full Python language and ecosystem
- Natural resource references (just pass objects)
- No compilation required
- Easier to extend and test
- Better IDE and debugging support
- Focus on unique features (drift, recording, AI)


## Release Notes

### 0.1.0 - "First Slice" 🍕

This is the initial release of Cook, a modern configuration management tool in Python.

**Highlights:**

- 🎉 Complete rewrite in Python (from Go + Starlark)
- 📦 4 core resources (File, Package, Service, Exec)
- 🔄 Service reload triggers
- 🚀 Fast setup with uv
- 📚 Comprehensive documentation

**What's Working:**

- Plan/apply workflow
- Platform detection
- Resource dependencies
- Idempotency
- Colored CLI output

**Beta (working but under development) **

- SSH transport for remote deployment
- State persistence for history tracking
- Drift monitoring (unique feature!)
- Recording mode (capture manual changes)
- MCP server - transform Agents into safe DevOps Engineers

**Try it out:**

```bash
# Install
uv venv && uv pip install -e .

# Run example
cook plan examples/simple.py
cook apply examples/simple.py
```
