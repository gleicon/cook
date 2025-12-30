# Cook Migration Summary

## Changes Made (2025-12-29)

### 1. Migrated to UV Dependency Management ✅

**Previous state:**
- Using setuptools as build backend
- `uv.lock` file untracked in git
- No clear dependency management strategy

**New state:**
- Migrated from setuptools to `hatchling` build backend (better uv compatibility)
- Added `rich>=13.0.0` as core dependency for logging
- `uv.lock` now tracked in git for reproducible builds
- All dependencies installed with `uv sync` or `uv sync --all-extras`
- Updated `.gitignore` to exclude `.python-version` (uv-specific)

**Commands:**
```bash
# Install dependencies
uv sync

# Install with all optional dependencies (templates, ssh, state, record, dev)
uv sync --all-extras

# Run cook CLI
uv run cook --help

# Run tests
uv run pytest
```

### 2. Implemented Centralized Logging System ✅

**Previous state:**
- Scattered `print()` statements throughout codebase
- Direct ANSI escape codes (`\033[91m`, `\033[93m`, etc.)
- No structured logging or verbosity control
- Inconsistent formatting

**New state:**
- Centralized logging module: `cook/logging.py`
- Built on Python's `logging` module with `rich` formatting
- Two logger types:
  - `get_logger(__name__)` - Standard Python logger with rich formatting
  - `get_cook_logger(__name__)` - Enhanced logger with Cook-specific methods
- Special formatting methods:
  - `logger.success()` - Green checkmark for successes
  - `logger.action()` - Resource actions with symbols (+/~/-)
  - `logger.security_warning()` - Prominent security warnings
  - `logger.dry_run()` - Dry-run mode indicators
  - `logger.resource_status()` - Status updates with timing
  - `logger.table_row()` / `logger.separator()` - Formatted tables

**CLI flags:**
```bash
# Default (INFO level)
cook plan server.py

# Debug mode
cook --debug plan server.py

# Quiet mode (errors only)
cook --quiet apply server.py
```

### 3. Updated Files

**Core modules:**
- `cook/__init__.py` - Added logging exports
- `cook/core/__init__.py` - Created (was missing)
- `cook/core/executor.py` - Replaced print with logger.info
- `cook/logging.py` - New centralized logging module

**Resource modules:**
- `cook/resources/exec.py` - Replaced ANSI codes with logger methods

**CLI:**
- `cook/cli/main.py` - Added logging setup, --debug and --quiet flags

**Recording:**
- `cook/record/recorder.py` - Replaced print statements with logging

**Configuration:**
- `pyproject.toml` - Migrated to hatchling, added rich dependency
- `.gitignore` - Added uv-specific entries
- `uv.lock` - Now tracked in git

**Documentation:**
- `docs/LOGGING.md` - Comprehensive logging documentation

### 4. Benefits

**Developer experience:**
- ✅ Structured, consistent logging across codebase
- ✅ No more ANSI code management
- ✅ Easy verbosity control via CLI flags
- ✅ Better debugging with rich tracebacks
- ✅ Professional, polished output

**Maintainability:**
- ✅ Centralized logging configuration
- ✅ Easy to add new log formats
- ✅ Type-safe logging methods
- ✅ Consistent API across all modules

**User experience:**
- ✅ Beautiful, readable output with colors and formatting
- ✅ Clear visual hierarchy (success, warnings, errors)
- ✅ Adjustable verbosity for different use cases
- ✅ Professional appearance

**Dependency management:**
- ✅ Reproducible builds with `uv.lock`
- ✅ Fast dependency resolution with uv
- ✅ Clear separation of core vs optional dependencies
- ✅ Modern Python tooling

## Migration Guide for Contributors

### Using the Logger

**Before:**
```python
print(f"Creating resource: {name}")
print(f"\033[91mERROR: {error}\033[0m")
print(f"\033[93mWARNING: {warning}\033[0m")
```

**After:**
```python
from cook.logging import get_cook_logger

logger = get_cook_logger(__name__)
logger.info(f"Creating resource: {name}")
logger.error(f"ERROR: {error}")
logger.warning(f"WARNING: {warning}")

# Or use special methods:
logger.action("create", name)
logger.security_warning(f"ERROR: {error}", resource=name)
```

### Adding New Features

1. Import logger at module level:
```python
from cook.logging import get_cook_logger

logger = get_cook_logger(__name__)
```

2. Use appropriate log levels:
- `logger.debug()` - Detailed diagnostics
- `logger.info()` - Progress updates
- `logger.warning()` - Potential issues
- `logger.error()` - Failures
- `logger.critical()` - Critical failures

3. Use special methods for common patterns:
- `logger.success()` - Success messages
- `logger.action()` - Resource actions
- `logger.security_warning()` - Security warnings
- `logger.dry_run()` - Dry-run operations

### Testing Changes

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Test CLI
uv run cook --help
uv run cook --debug plan examples/simple.py

# Verify logging
uv run python -c "
from cook.logging import get_cook_logger
logger = get_cook_logger('test')
logger.success('Test successful')
logger.action('create', 'file[/etc/test.conf]')
logger.security_warning('Test warning', 'test-resource')
"
```

## Breaking Changes

None. This is a backward-compatible internal refactoring. The CLI interface remains unchanged (except for the addition of `--debug` and `--quiet` flags).

## Next Steps

1. ✅ All print statements replaced with logging
2. ✅ All ANSI codes replaced with rich formatting
3. ✅ Documentation created
4. Consider: Add logging configuration file support (future)
5. Consider: Add JSON/structured logging output option (future)
6. Consider: Add logging to file option (future)

## References

- [UV Documentation](https://github.com/astral-sh/uv)
- [Rich Documentation](https://rich.readthedocs.io/)
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Cook Logging Documentation](docs/LOGGING.md)
