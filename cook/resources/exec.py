"""
Exec resource - run arbitrary commands.

Used for tasks that don't fit other resources:
- Database setup
- Application deployment
- Custom scripts

SECURITY WARNING:
    Commands are executed via shell (shell=True) to support pipes,
    redirects, and shell features. Only use this resource with
    trusted input. Never pass unsanitized user input to commands.

    Safe:
        Exec("backup", command="tar czf /backup/data.tar.gz /var/data")

    Unsafe:
        user_file = input()  # User input!
        Exec("backup", command=f"tar czf /backup/{user_file}")  # DANGEROUS!
"""

import hashlib
from typing import Dict, Any, Optional

from cook.core.resource import Resource, Plan, Action, Platform
from cook.core.executor import get_executor


class Exec(Resource):
    """
    Exec resource for running commands.

    Idempotency guards:
    - creates: Run only if file/dir doesn't exist
    - unless: Run only if command returns non-zero
    - only_if: Run only if command returns zero
    - checksum: Track command changes via checksum

    Examples:
        # Run once (creates guard)
        Exec("setup-db",
             command="mysql < /tmp/schema.sql",
             creates="/var/lib/mysql/mydb")

        # Conditional execution
        Exec("install-composer",
             command="curl -sS https://getcomposer.org/installer | php",
             unless="which composer")

        # Always run (use with caution!)
        Exec("deploy",
             command="./deploy.sh")
    """

    def __init__(
        self,
        name: str,
        command: str,
        creates: Optional[str] = None,
        unless: Optional[str] = None,
        only_if: Optional[str] = None,
        cwd: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        **options
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
            **options: Additional options
        """
        super().__init__(name, **options)

        self.command = command
        self.creates = creates
        self.unless = unless
        self.only_if = only_if
        self.cwd = cwd
        self.environment = environment or {}

        # Auto-register
        get_executor().add(self)

    def resource_type(self) -> str:
        return "exec"

    def check(self, platform: Platform) -> Dict[str, Any]:
        """Check if exec should run."""
        should_run = True

        # Check 'creates' guard
        if self.creates:
            if self._transport.file_exists(self.creates):
                should_run = False

        # Check 'unless' guard
        if should_run and self.unless:
            output, code = self._transport.run_shell(self.unless)
            if code == 0:
                should_run = False

        # Check 'only_if' guard
        if should_run and self.only_if:
            output, code = self._transport.run_shell(self.only_if)
            if code != 0:
                should_run = False

        return {
            "exists": True,
            "should_run": should_run,
            "command_hash": self._hash_command(),
        }

    def desired_state(self) -> Dict[str, Any]:
        """Exec desired state: should_run=False means 'not yet executed'."""
        return {
            "exists": True,
            "should_run": False,  # Desired is "not running" so actual=True creates change
            "command_hash": self._hash_command(),
        }

    def apply(self, plan: Plan, platform: Platform) -> None:
        """Execute command."""
        if not self._actual_state.get("should_run", True):
            return

        # Build command with environment variables and cwd
        cmd = self.command
        if self.environment:
            env_str = " ".join(f"{k}={v}" for k, v in self.environment.items())
            cmd = f"{env_str} {cmd}"

        if self.cwd:
            cmd = f"cd {self.cwd} && {cmd}"

        # Run command
        output, code = self._transport.run_shell(cmd)

        if code != 0:
            raise RuntimeError(
                f"Command failed with exit code {code}\n"
                f"Output: {output}"
            )

    def _hash_command(self) -> str:
        """Generate hash of command for change detection."""
        return hashlib.sha256(self.command.encode()).hexdigest()[:8]
