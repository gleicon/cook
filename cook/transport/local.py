"""
Local transport - run commands on local machine.
"""

import subprocess
from pathlib import Path
from typing import Tuple


class LocalTransport:
    """
    Local transport for running commands on the local machine.

    Uses subprocess for command execution.
    """

    def run_shell(self, command: str) -> Tuple[str, int]:
        """
        Run command via shell.

        Args:
            command: Shell command string

        Returns:
            Tuple of (output, exit_code)
        """
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )
        return result.stdout + result.stderr, result.returncode

    def run_command(self, args: list) -> Tuple[str, int]:
        """
        Run command from list of arguments (safer - no shell).

        Args:
            args: Command and arguments as list

        Returns:
            Tuple of (output, exit_code)
        """
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
        )
        return result.stdout + result.stderr, result.returncode

    def write_file(self, path: str, content: bytes) -> None:
        """Write content to file."""
        Path(path).write_bytes(content)

    def read_file(self, path: str) -> bytes:
        """Read file content."""
        return Path(path).read_bytes()

    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return Path(path).exists()

    def copy_file(self, local_path: str, remote_path: str) -> None:
        """
        Copy file locally.

        Args:
            local_path: Source path
            remote_path: Destination path
        """
        content = Path(local_path).read_bytes()
        Path(remote_path).write_bytes(content)

    def close(self) -> None:
        """No-op for local transport."""
        pass
