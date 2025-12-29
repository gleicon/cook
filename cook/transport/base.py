"""
Base transport interface.

All transport implementations (Local, SSH) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Tuple


class Transport(ABC):
    """
    Abstract base class for command running and file operations.

    Implementations:
    - LocalTransport: Run commands locally
    - SSHTransport: Run commands on remote host via SSH
    """

    @abstractmethod
    def run_shell(self, command: str) -> Tuple[str, int]:
        """
        Run a command via shell and return output and exit code.

        Args:
            command: Command to run (as shell string)

        Returns:
            Tuple of (output, exit_code)

        Example:
            output, code = transport.run_shell("ls -la /tmp")
        """
        pass

    @abstractmethod
    def run_command(self, args: list) -> Tuple[str, int]:
        """
        Run a command from list of arguments (safer - no shell).

        Args:
            args: Command and arguments as list

        Returns:
            Tuple of (output, exit_code)

        Example:
            output, code = transport.run_command(["ls", "-la", "/tmp"])
        """
        pass

    @abstractmethod
    def write_file(self, remote_path: str, content: bytes) -> None:
        """
        Write content to a file.

        Args:
            remote_path: Path to file (may be remote)
            content: File content as bytes

        Raises:
            IOError: If write fails
        """
        pass

    @abstractmethod
    def read_file(self, remote_path: str) -> bytes:
        """
        Read file content.

        Args:
            remote_path: Path to file (may be remote)

        Returns:
            File content as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists.

        Args:
            remote_path: Path to file (may be remote)

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    def copy_file(self, local_path: str, remote_path: str) -> None:
        """
        Copy file from local to remote.

        Args:
            local_path: Local file path
            remote_path: Remote file path

        Raises:
            FileNotFoundError: If local file doesn't exist
            IOError: If copy fails
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close transport connection.

        For LocalTransport this is a no-op.
        For SSHTransport this closes the SSH connection.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()
