"""
Exec resource - run arbitrary commands.

SECURITY WARNING:
    Commands are executed via shell (shell=True) to support pipes,
    redirects, and shell features. Only use this resource with
    trusted input. Never pass unsanitized user input to commands.

    Safe:
        Exec("backup", command="tar czf /backup/data.tar.gz /var/data")

    Unsafe:
        user_file = input()  # User input!
        Exec("backup", command=f"tar czf /backup/{user_file}")  # DANGEROUS!

SECURITY FEATURES:
    - dry_run=True: Preview commands without execution
    - safe_mode=True: Validate commands for injection patterns
    - Security warnings for dangerous patterns
"""

import hashlib
import re
import shlex
from enum import Enum
from typing import Any, Dict, List, Optional

from cook.core.executor import get_executor
from cook.core import Plan, Platform, Resource
from cook.logging import get_cook_logger

logger = get_cook_logger(__name__)


class SecurityLevel(Enum):
    """Security validation levels."""

    NONE = "none"  # No validation (dangerous)
    WARN = "warn"  # Warn but allow
    STRICT = "strict"  # Block dangerous patterns


class SecurityViolation(Exception):
    """Raised when command fails security validation."""

    pass


class Exec(Resource):
    """
    Exec resource for running commands.

    Idempotency guards:
    - creates: Run only if file/dir doesn't exist
    - unless: Run only if command returns non-zero
    - only_if: Run only if command returns zero
    - checksum: Track command changes via checksum

    Security options:
    - dry_run: Preview without execution
    - safe_mode: Enable strict security validation
    - security_level: NONE, WARN, or STRICT

    Examples:
        # Run once (creates guard)
        Exec("setup-db",
             command="mysql < /tmp/schema.sql",
             creates="/var/lib/mysql/mydb")

        # Conditional execution
        Exec("install-composer",
             command="curl -sS https://getcomposer.org/installer | php",
             unless="which composer")

        # Dry run mode
        Exec("deploy",
             command="./deploy.sh",
             dry_run=True)  # Preview only

        # Safe mode (validates for injection)
        Exec("backup",
             command="tar czf /backup/data.tar.gz /var/data",
             safe_mode=True)
    """

    # Dangerous shell metacharacters and patterns
    DANGEROUS_PATTERNS = [
        r";",  # Command chaining
        r"\&\&",  # Conditional execution
        r"\|\|",  # Conditional execution
        r"\|",  # Pipe (allow if explicitly permitted)
        r"\$\(",  # Command substitution
        r"`",  # Backtick command substitution
        r"\$\{",  # Variable expansion
        r">",  # Redirect (allow if explicitly permitted)
        r"<",  # Redirect (allow if explicitly permitted)
        r"\n",  # Newline injection
        r"\r",  # Carriage return
    ]

    # Dangerous commands that should trigger warnings
    DANGEROUS_COMMANDS = [
        r"\brm\s+-rf\s+/",  # Recursive delete from root
        r"\bdd\s+if=/dev/",  # Disk operations
        r"\bmkfs\.",  # Format filesystem
        r"\b:\(\)\{\s*:\|:\&\s*\};:",  # Fork bomb
        r"\bchmod\s+777",  # World-writable
        r"\bchown\s+.*root",  # Change to root
        r"curl.*\|\s*(bash|sh)",  # Pipe to shell
        r"wget.*\|\s*(bash|sh)",  # Pipe to shell
        r"\beval\s",  # Eval injection
        r"/dev/sd[a-z]",  # Direct disk access
    ]

    def __init__(
        self,
        name: str,
        command: str,
        creates: Optional[str] = None,
        unless: Optional[str] = None,
        only_if: Optional[str] = None,
        cwd: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
        safe_mode: bool = True,  # SECURE BY DEFAULT
        security_level: str = "strict",  # STRICT BY DEFAULT
        allow_pipes: bool = True,
        allow_redirects: bool = True,
        **options,
    ):
        """
        Initialize exec resource.

        Args:
            name: Resource name/description
            command: Command to execute
            creates: Only run if this file doesn't exist
            unless: Only run if this command fails
            only_if: Only run if this command succeeds
            cwd: Working directory
            environment: Environment variables
            dry_run: Preview mode - don't execute (default: False)
            safe_mode: Enable strict security validation (default: True - RECOMMENDED)
            security_level: "none", "warn", or "strict" (default: "strict")
            allow_pipes: Allow pipe (|) in commands (default: True)
            allow_redirects: Allow redirects (>, <) in commands (default: True)
            **options: Additional options
        """
        super().__init__(name, **options)

        self.command = command
        self.creates = creates
        self.unless = unless
        self.only_if = only_if
        self.cwd = cwd
        self.environment = environment or {}
        self.dry_run = dry_run
        self.safe_mode = safe_mode
        self.allow_pipes = allow_pipes
        self.allow_redirects = allow_redirects

        # Parse security level
        try:
            self.security_level = SecurityLevel(security_level.lower())
        except ValueError:
            self.security_level = SecurityLevel.STRICT  # Default to strict

        # In safe_mode, automatically set strict security
        if self.safe_mode:
            self.security_level = SecurityLevel.STRICT

        # IMPORTANT: Warn when safe_mode is explicitly disabled
        if not self.safe_mode:
            warning_msg = (
                f"safe_mode=False disables security validation\n"
                f"  Command: {self.command[:60]}{'...' if len(self.command) > 60 else ''}\n"
                f"  This is DANGEROUS and should only be used with fully trusted input.\n"
                f"  Set safe_mode=True (default) for security validation."
            )
            logger.security_warning(warning_msg, resource=f"Exec resource '{self.name}' is running in UNSAFE MODE")

        # Validate inputs on initialization
        self._validate_security()

        # Auto-register
        get_executor().add(self)

    def resource_type(self) -> str:
        return "exec"

    def _validate_security(self) -> None:
        """
        Validate all command inputs for security issues.

        Raises:
            SecurityViolation: If strict mode and dangerous patterns found
        """
        if self.security_level == SecurityLevel.NONE:
            return

        issues: List[str] = []

        # Check main command
        cmd_issues = self._check_command_security(self.command, "command")
        issues.extend(cmd_issues)

        # Check guard commands
        if self.unless:
            issues.extend(self._check_command_security(self.unless, "unless"))
        if self.only_if:
            issues.extend(self._check_command_security(self.only_if, "only_if"))

        # Check working directory
        if self.cwd:
            issues.extend(self._check_path_security(self.cwd, "cwd"))

        # Check environment variables
        for key, value in self.environment.items():
            issues.extend(self._check_env_security(key, value))

        # Check creates path
        if self.creates:
            issues.extend(self._check_path_security(self.creates, "creates"))

        if issues:
            msg = f"\n[SECURITY] Exec resource '{self.name}' has security concerns:\n"
            msg += "\n".join(f"  - {issue}" for issue in issues)

            if self.security_level == SecurityLevel.STRICT:
                msg += "\n\nSet security_level='warn' or 'none' to bypass (NOT RECOMMENDED)"
                raise SecurityViolation(msg)
            else:
                # Just warn
                logger.warning(msg)

    def _check_command_security(self, cmd: str, context: str) -> List[str]:
        """Check command for security issues."""
        issues = []

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            # Skip allowed patterns
            if pattern == r"\|" and self.allow_pipes:
                continue
            if pattern in [r">", r"<"] and self.allow_redirects:
                continue

            if re.search(pattern, cmd):
                issues.append(
                    f"{context}: Contains dangerous pattern '{pattern.replace(chr(92), '')}' in: {cmd[:50]}..."
                )

        # Check for dangerous commands
        for pattern in self.DANGEROUS_COMMANDS:
            if re.search(pattern, cmd, re.IGNORECASE):
                issues.append(
                    f"{context}: Contains dangerous command pattern matching '{pattern}'"
                )

        # Check for environment variable injection
        if "$" in cmd and "${" not in cmd and "$(" not in cmd:
            # Shell variable reference - potential injection
            issues.append(
                f"{context}: Contains shell variable reference - potential injection"
            )

        return issues

    def _check_path_security(self, path: str, context: str) -> List[str]:
        """Check path for security issues."""
        issues = []

        # Check for command injection in paths
        dangerous = [";", "&", "|", "$", "`", "\n", "\r"]
        for char in dangerous:
            if char in path:
                issues.append(
                    f"{context}: Path contains dangerous character '{char}': {path}"
                )

        # Check for directory traversal
        if ".." in path:
            issues.append(f"{context}: Path contains directory traversal (..): {path}")

        # Check for null bytes
        if "\x00" in path:
            issues.append(f"{context}: Path contains null byte")

        return issues

    def _check_env_security(self, key: str, value: str) -> List[str]:
        """Check environment variable for security issues."""
        issues = []

        # Check key
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            issues.append(
                f"environment: Invalid variable name '{key}' (must be alphanumeric)"
            )

        # Check value for command injection
        dangerous = [";", "&", "|", "$", "`", "\n", "\r"]
        for char in dangerous:
            if char in value:
                issues.append(
                    f"environment: Variable '{key}' contains dangerous character '{char}'"
                )

        return issues

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check if exec should run."""
        should_run = True
        warnings = []

        # Check 'creates' guard
        if self.creates:
            if self._transport.file_exists(self.creates):
                should_run = False

        # Check 'unless' guard (skip in dry-run)
        if should_run and self.unless and not self.dry_run:
            try:
                _, code = self._transport.run_shell(self.unless)
                if code == 0:
                    should_run = False
            except Exception as e:
                warnings.append(f"unless guard failed: {e}")

        # Check 'only_if' guard (skip in dry-run)
        if should_run and self.only_if and not self.dry_run:
            try:
                _, code = self._transport.run_shell(self.only_if)
                if code != 0:
                    should_run = False
            except Exception as e:
                warnings.append(f"only_if guard failed: {e}")

        return {
            "exists": True,
            "should_run": should_run,
            "command_hash": self._hash_command(),
            "dry_run": self.dry_run,
            "warnings": warnings,
        }

    def desired_state(self) -> Dict[str, Any]:
        """Exec desired state: should_run=False means 'not yet executed'."""
        return {
            "exists": True,
            "should_run": False,  # Desired is "not running" so actual=True creates change
            "command_hash": self._hash_command(),
            "dry_run": self.dry_run,
            "warnings": [],
        }

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Execute command."""
        if not self._actual_state.get("should_run", True):
            return

        # Build final command
        final_cmd = self._build_command()

        # Dry run mode - just preview
        if self.dry_run:
            logger.dry_run(f"Would execute for '{self.name}':")
            logger.info(f"  Command: {final_cmd}")
            if self.cwd:
                logger.info(f"  Working directory: {self.cwd}")
            if self.environment:
                logger.info(f"  Environment: {self.environment}")
            logger.info(f"  (Not executed - dry_run=True)")
            return

        # Warn again before execution if unsafe mode
        if not self.safe_mode:
            logger.security_warning(f"EXECUTING IN UNSAFE MODE: {self.name}")

        # Execute command
        output, code = self._transport.run_shell(final_cmd)

        if code != 0:
            raise RuntimeError(
                f"Command failed with exit code {code}\n"
                f"Command: {final_cmd}\n"
                f"Output: {output}"
            )

    def _build_command(self) -> str:
        """
        Build final command with environment and cwd.

        Uses safer construction to minimize injection risk.
        """
        cmd = self.command

        # Add environment variables using safer quoting
        if self.environment:
            env_parts = []
            for key, value in self.environment.items():
                # Quote values to prevent word splitting
                # Note: shlex.quote() prevents most injection
                quoted_value = shlex.quote(value)
                env_parts.append(f"{key}={quoted_value}")

            env_str = " ".join(env_parts)
            cmd = f"{env_str} {cmd}"

        # Add working directory with safer construction
        if self.cwd:
            # Quote the directory path
            quoted_cwd = shlex.quote(self.cwd)
            cmd = f"cd {quoted_cwd} && {cmd}"

        return cmd

    def _hash_command(self) -> str:
        """Generate hash of command for change detection."""
        # Include all parameters that affect execution
        hash_input = f"{self.command}:{self.cwd}:{self.environment}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:8]

    def preview(self) -> str:
        """
        Preview the command that would be executed.

        Returns:
            The final command string
        """
        return self._build_command()

    def get_security_report(self) -> Dict[str, Any]:
        """
        Get detailed security analysis of this resource.

        Returns:
            Dictionary with security analysis
        """
        issues = []

        # Collect all issues
        issues.extend(self._check_command_security(self.command, "command"))
        if self.unless:
            issues.extend(self._check_command_security(self.unless, "unless"))
        if self.only_if:
            issues.extend(self._check_command_security(self.only_if, "only_if"))
        if self.cwd:
            issues.extend(self._check_path_security(self.cwd, "cwd"))
        for key, value in self.environment.items():
            issues.extend(self._check_env_security(key, value))

        return {
            "resource": self.name,
            "command": self.command,
            "security_level": self.security_level.value,
            "safe_mode": self.safe_mode,
            "dry_run": self.dry_run,
            "issues": issues,
            "risk_level": "high"
            if len(issues) > 3
            else "medium"
            if len(issues) > 0
            else "low",
        }
