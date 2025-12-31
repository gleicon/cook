"""
Logging for Cook.

Example:
    from cook.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Starting execution")
    logger.warning("Resource has drifted")
    logger.error("Failed to apply changes", exc_info=True)
"""

import logging
import sys
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Custom theme for Cook
COOK_THEME = Theme({
    "log.time": "dim cyan",
    "log.level.debug": "dim blue",
    "log.level.info": "green",
    "log.level.warning": "yellow",
    "log.level.error": "bold red",
    "log.level.critical": "bold white on red",
    "cook.success": "bold green",
    "cook.action.create": "green",
    "cook.action.update": "yellow",
    "cook.action.delete": "red",
    "cook.security": "bold red",
    "cook.dry_run": "cyan",
})

# Global console instance
console = Console(theme=COOK_THEME, stderr=True)

# Flag to track if logging has been initialized
_initialized = False


def setup_logging(
    level: str = "INFO",
    show_time: bool = True,
    show_path: bool = False,
    rich_tracebacks: bool = True,
) -> None:
    """
    init Cook's logging

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        show_time: Show timestamps in log output
        show_path: Show file path in log output
        rich_tracebacks: Use rich formatting for tracebacks

    Note:
        This should be called once at application startup.
        Subsequent calls will be ignored to prevent duplicate handlers.
    """
    global _initialized

    if _initialized:
        return

    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure rich handler
    handler = RichHandler(
        console=console,
        show_time=show_time,
        show_path=show_path,
        rich_tracebacks=rich_tracebacks,
        markup=True,
        tracebacks_show_locals=True,
    )

    # Set format
    handler.setFormatter(
        logging.Formatter(
            "%(message)s",
            datefmt="[%X]",
        )
    )

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=[handler],
        force=True,  # Override any existing configuration
    )

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a given module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing resource")
    """
    # Ensure logging is initialized
    if not _initialized:
        setup_logging()

    return logging.getLogger(name)


class CookLogger:
    """
    Cook-specific logger

    Wraps standard logger with convenience methods for common Cook operations.
    """

    def __init__(self, name: str):
        """
        Initialize Cook logger.

        Args:
            name: Logger name (typically __name__)
        """
        self.logger = get_logger(name)
        self.console = console

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)

    def success(self, message: str) -> None:
        """
        Log success message with special formatting.

        Args:
            message: Success message to display
        """
        self.console.print(f"[cook.success]✓[/cook.success] {message}")

    def action(self, action: str, resource_id: str, details: Optional[str] = None) -> None:
        """
        Log resource action (create/update/delete).

        Args:
            action: Action type (create, update, delete)
            resource_id: Resource identifier
            details: Optional details about the action
        """
        from rich.markup import escape

        symbols = {
            "create": "+",
            "update": "~",
            "delete": "-",
        }
        symbol = symbols.get(action.lower(), "•")
        style = f"cook.action.{action.lower()}"

        # Escape resource_id to prevent markup interpretation
        msg = f"[{style}]{symbol}[/{style}] {escape(resource_id)}"
        if details:
            msg += f" [dim]({escape(details)})[/dim]"

        self.console.print(msg)

    def security_warning(self, message: str, resource: Optional[str] = None) -> None:
        """
        Log security warning

        Args:
            message: Security warning message
            resource: Optional resource name
        """
        separator = "-" * 70
        header = f"\n{separator}\n"
        header += "SECURITY WARNING"
        if resource:
            header += f": {resource}"
        header += f"\n{separator}"

        self.console.print(f"[cook.security]{header}[/cook.security]")
        self.console.print(f"[cook.security]{message}[/cook.security]")
        self.console.print(f"[cook.security]{separator}[/cook.security]\n")

    def dry_run(self, message: str) -> None:
        """
        Log dry-run 

        Args:
            message: Dry-run message to display
        """
        self.console.print(f"[cook.dry_run][DRY RUN][/cook.dry_run] {message}")

    def resource_status(self, resource_id: str, status: str, duration: Optional[float] = None) -> None:
        """
        Log resource status update.

        Args:
            resource_id: Resource identifier
            status: Status message
            duration: Optional duration in seconds
        """
        from rich.markup import escape

        msg = f"  {escape(resource_id)} ... {escape(status)}"
        if duration:
            msg += f" [dim]({duration:.2f}s)[/dim]"

        if "done" in status.lower() or "success" in status.lower():
            self.console.print(f"[cook.success]{msg}[/cook.success]")
        else:
            self.console.print(msg)

    def table_row(self, *columns, widths: Optional[list[int]] = None) -> None:
        """
        Print a table row (for status listings).

        Args:
            *columns: Column values
            widths: Optional column widths
        """
        if widths:
            row = "  ".join(str(col).ljust(w) for col, w in zip(columns, widths))
        else:
            row = "  ".join(str(col) for col in columns)

        self.console.print(row)

# Convenience function to get CookLogger
def get_cook_logger(name: str) -> CookLogger:
    """
    Get a CookLogger instance for the given module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        CookLogger instance

    Example:
        logger = get_cook_logger(__name__)
        logger.success("Resource applied successfully")
        logger.action("create", "file[/etc/nginx.conf]")
    """
    return CookLogger(name)
