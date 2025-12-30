# Cook Logging System

Cook uses a centralized logging system built on Python's `logging` module with rich formatting via the `rich` library.

## Overview

The logging system replaces all previous `print()`, `printf()`, and ANSI escape code statements with a structured, configurable logging framework that provides:

- **Structured logging** with multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Rich formatting** with colors, styles, and visual hierarchy
- **Context-aware output** with special formatting for security warnings, dry-run mode, and resource actions
- **Configurable verbosity** via command-line flags

## Basic Usage

### In Your Code

```python
from cook.logging import get_logger, get_cook_logger

# Standard Python logger
logger = get_logger(__name__)
logger.info("Processing resource")
logger.warning("Resource has drifted")
logger.error("Failed to apply changes", exc_info=True)

# Enhanced Cook logger with special formatting
logger = get_cook_logger(__name__)
logger.success("Resource applied successfully")
logger.action("create", "file[/etc/nginx.conf]")
logger.security_warning("Unsafe mode enabled", resource="exec-resource")
logger.dry_run("Would execute command: apt-get install nginx")
```

### CLI Configuration

Control logging verbosity from the command line:

```bash
# Default INFO level
cook plan server.py

# Debug mode (verbose output)
cook --debug plan server.py

# Quiet mode (errors only)
cook --quiet apply server.py
```

## Logger Types

### Standard Logger (`get_logger`)

Returns a standard Python `logging.Logger` instance with rich formatting:

```python
from cook.logging import get_logger

logger = get_logger(__name__)
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical issue")
```

### Cook Logger (`get_cook_logger`)

Returns an enhanced `CookLogger` instance with Cook-specific formatting:

```python
from cook.logging import get_cook_logger

logger = get_cook_logger(__name__)
```

#### Special Methods

##### `success(message)`
Log success messages with green checkmark:
```python
logger.success("Resource applied successfully")
# Output: ✓ Resource applied successfully
```

##### `action(action, resource_id, details=None)`
Log resource actions (create/update/delete):
```python
logger.action("create", "file[/etc/nginx.conf]")
logger.action("update", "service[nginx]", details="reloaded")
logger.action("delete", "package[apache2]")
# Output:
# + file[/etc/nginx.conf]
# ~ service[nginx] (reloaded)
# - package[apache2]
```

##### `security_warning(message, resource=None)`
Display prominent security warnings:
```python
logger.security_warning(
    "safe_mode=False disables security validation",
    resource="exec-resource"
)
# Output:
# ======================================================================
# SECURITY WARNING: exec-resource
# ======================================================================
# safe_mode=False disables security validation
# ======================================================================
```

##### `dry_run(message)`
Indicate dry-run mode operations:
```python
logger.dry_run("Would execute command: apt-get install nginx")
# Output: [DRY RUN] Would execute command: apt-get install nginx
```

##### `resource_status(resource_id, status, duration=None)`
Log resource status updates:
```python
logger.resource_status("file[/etc/nginx.conf]", "done", duration=0.45)
# Output:   file[/etc/nginx.conf] ... done (0.45s)
```

##### `table_row(*columns, widths=None)`
Print formatted table rows:
```python
logger.table_row("RESOURCE", "STATUS", "LAST APPLIED", widths=[40, 12, 20])
logger.separator()
logger.table_row("file[/etc/nginx.conf]", "success", "2025-01-01 12:00")
```

##### `separator(char="-", length=80)`
Print separator lines:
```python
logger.separator()          # Default: 80 hyphens
logger.separator("=", 50)   # 50 equals signs
```

## Configuration

### Setup Logging

Initialize logging at application startup:

```python
from cook.logging import setup_logging

# Default INFO level, no timestamps
setup_logging()

# Debug mode with timestamps
setup_logging(level="DEBUG", show_time=True)

# Quiet mode, errors only
setup_logging(level="ERROR", show_time=False)

# Development mode with full context
setup_logging(
    level="DEBUG",
    show_time=True,
    show_path=True,
    rich_tracebacks=True
)
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical issues requiring immediate attention

## Color Theme

Cook uses a custom color theme for consistent visual hierarchy:

- **Success**: Bold green
- **Create action**: Green `+`
- **Update action**: Yellow `~`
- **Delete action**: Red `-`
- **Security warnings**: Bold red with separator
- **Dry run**: Cyan
- **Errors**: Bold red
- **Warnings**: Yellow

## Migration from Print Statements

### Before
```python
print(f"Creating resource: {name}")
print(f"\033[91mERROR: {error}\033[0m")  # Red ANSI
print(f"\033[93mWARNING: {warning}\033[0m")  # Yellow ANSI
```

### After
```python
logger.info(f"Creating resource: {name}")
logger.error(f"ERROR: {error}")
logger.warning(f"WARNING: {warning}")
```

## Best Practices

1. **Use appropriate log levels**
   - DEBUG: Detailed diagnostics
   - INFO: Progress updates, status changes
   - WARNING: Potential issues, drift detected
   - ERROR: Failures that stop execution
   - CRITICAL: System-level failures

2. **Include context in messages**
   ```python
   # Good
   logger.info(f"Applying resource: {resource.id}")

   # Better
   logger.action("update", resource.id, details="configuration changed")
   ```

3. **Use structured formatting**
   ```python
   # Use special methods for common patterns
   logger.success("Resource applied")           # Not logger.info("✓ Resource applied")
   logger.action("create", resource_id)          # Not logger.info(f"+ {resource_id}")
   logger.security_warning(msg, resource)        # Not print with ANSI codes
   ```

4. **Avoid string formatting for large objects**
   ```python
   # Good
   logger.debug("Resource state: %s", resource.state)

   # Bad (formats even if debug is disabled)
   logger.debug(f"Resource state: {resource.state}")
   ```

5. **Use exc_info for exceptions**
   ```python
   try:
       apply_resource()
   except Exception as e:
       logger.error("Failed to apply resource", exc_info=True)
   ```

## Performance Considerations

- Logging is lazy-evaluated when using `%s` formatting
- Rich formatting only renders when messages are output
- Debug messages are skipped entirely when not in debug mode
- Use `logger.debug()` generously without performance concerns

## Examples

### Resource Application
```python
logger = get_cook_logger(__name__)

logger.info("Planning resource changes...")
for resource in resources:
    logger.action("create", resource.id)

logger.info("\nApplying changes...")
for resource in changed_resources:
    try:
        resource.apply()
        logger.resource_status(resource.id, "done", duration=0.5)
    except Exception as e:
        logger.error(f"Failed to apply {resource.id}", exc_info=True)

logger.success(f"Apply complete! Changed {len(changed_resources)} resources")
```

### Security Validation
```python
logger = get_cook_logger(__name__)

if not safe_mode:
    logger.security_warning(
        "safe_mode=False disables security validation\n"
        f"  Command: {command}\n"
        "  This is DANGEROUS with untrusted input.",
        resource=f"Exec resource '{name}'"
    )
```

### Dry Run Mode
```python
logger = get_cook_logger(__name__)

if dry_run:
    logger.dry_run(f"Would execute: {command}")
    logger.info(f"  Working directory: {cwd}")
    logger.info(f"  Environment: {env}")
    return
```
