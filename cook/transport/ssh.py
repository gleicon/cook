"""
SSH transport - run commands on remote hosts via SSH.
"""

import os
from pathlib import Path
from typing import Tuple, Optional
import paramiko

from cook.transport.base import Transport


class SSHTransport(Transport):
    """
    SSH transport for running commands on remote hosts.

    Uses Paramiko for SSH connectivity.

    Example:
        transport = SSHTransport(
            host="server.example.com",
            user="admin",
            key_file="~/.ssh/id_rsa"
        )

        with transport:
            output, code = transport.run_command(["ls", "-la"])
            print(output)
    """

    def __init__(
        self,
        host: str,
        port: int = 22,
        user: Optional[str] = None,
        password: Optional[str] = None,
        key_file: Optional[str] = None,
        timeout: int = 30,
        sudo: bool = False,
    ):
        """
        Initialize SSH transport.

        Args:
            host: Remote hostname or IP
            port: SSH port (default: 22)
            user: SSH username (default: current user)
            password: SSH password (not recommended)
            key_file: Path to private key file
            timeout: Connection timeout in seconds
            sudo: Use sudo for all commands (default: False)
        """
        self.host = host
        self.port = port
        self.user = user or os.getenv("USER")
        self.password = password
        self.key_file = key_file
        self.timeout = timeout
        self.sudo = sudo
        self.client: Optional[paramiko.SSHClient] = None

        # Connect immediately
        self._connect()

    def _connect(self) -> None:
        """Establish SSH connection."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Prepare authentication
        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.user,
            "timeout": self.timeout,
        }

        # Password auth
        if self.password:
            connect_kwargs["password"] = self.password

        # Key-based auth
        if self.key_file:
            key_path = Path(self.key_file).expanduser()
            connect_kwargs["key_filename"] = str(key_path)

        # Connect
        self.client.connect(**connect_kwargs)

    def run_shell(self, command: str) -> Tuple[str, int]:
        """
        Run command via shell on remote host.

        Args:
            command: Shell command string

        Returns:
            Tuple of (output, exit_code)
        """
        # Prepend sudo if enabled
        if self.sudo:
            command = f"sudo -n {command}"

        stdin, stdout, stderr = self.client.exec_command(command)

        # Wait for command to complete
        exit_code = stdout.channel.recv_exit_status()

        # Get output
        output = stdout.read().decode() + stderr.read().decode()

        return output, exit_code

    def run_command(self, args: list) -> Tuple[str, int]:
        """
        Run command from list of arguments on remote host.

        Args:
            args: Command and arguments as list

        Returns:
            Tuple of (output, exit_code)
        """
        # Paramiko doesn't have direct list support, so we need to escape
        import shlex
        command = " ".join(shlex.quote(arg) for arg in args)

        # Prepend sudo if enabled
        if self.sudo:
            command = f"sudo -n {command}"

        return self.run_shell(command)

    def write_file(self, remote_path: str, content: bytes) -> None:
        """
        Write content to file on remote host.

        Args:
            remote_path: Path to file on remote host
            content: File content as bytes
        """
        if self.sudo:
            # When sudo is enabled, write to temp file then move with sudo
            import tempfile
            import hashlib

            # Generate unique temp filename
            file_hash = hashlib.md5(remote_path.encode()).hexdigest()[:8]
            temp_path = f"/tmp/cook-{file_hash}.tmp"

            # Write to temp location via SFTP (no sudo needed for /tmp)
            sftp = self.client.open_sftp()
            try:
                with sftp.open(temp_path, "wb") as f:
                    f.write(content)
            finally:
                sftp.close()

            # Create parent directory with sudo if needed
            parent = str(Path(remote_path).parent)
            self.run_command(["mkdir", "-p", parent])

            # Move to final location with sudo
            self.run_command(["mv", temp_path, remote_path])
        else:
            # Normal SFTP write (no sudo)
            sftp = self.client.open_sftp()
            try:
                # Create parent directory if needed
                parent = str(Path(remote_path).parent)
                try:
                    sftp.stat(parent)
                except FileNotFoundError:
                    # Create parent dirs
                    self.run_command(["mkdir", "-p", parent])

                # Write file
                with sftp.open(remote_path, "wb") as f:
                    f.write(content)
            finally:
                sftp.close()

    def read_file(self, remote_path: str) -> bytes:
        """
        Read file content from remote host.

        Args:
            remote_path: Path to file on remote host

        Returns:
            File content as bytes
        """
        sftp = self.client.open_sftp()
        try:
            with sftp.open(remote_path, "rb") as f:
                return f.read()
        finally:
            sftp.close()

    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists on remote host.

        Args:
            remote_path: Path to file on remote host

        Returns:
            True if file exists
        """
        if self.sudo:
            # When sudo is enabled, use test command which respects sudo
            output, code = self.run_command(["test", "-e", remote_path])
            return code == 0
        else:
            # Normal SFTP check (no sudo)
            sftp = self.client.open_sftp()
            try:
                sftp.stat(remote_path)
                return True
            except Exception:
                # Catch all exceptions, not just FileNotFoundError
                return False
            finally:
                sftp.close()

    def copy_file(self, local_path: str, remote_path: str) -> None:
        """
        Copy file from local to remote host via SCP/SFTP.

        Args:
            local_path: Local file path
            remote_path: Remote file path
        """
        if self.sudo:
            # When sudo is enabled, copy to temp location then move with sudo
            import hashlib

            # Generate unique temp filename
            file_hash = hashlib.md5(remote_path.encode()).hexdigest()[:8]
            temp_path = f"/tmp/cook-{file_hash}.tmp"

            # Copy to temp location via SFTP (no sudo needed for /tmp)
            sftp = self.client.open_sftp()
            try:
                sftp.put(local_path, temp_path)
            finally:
                sftp.close()

            # Create parent directory with sudo if needed
            parent = str(Path(remote_path).parent)
            self.run_command(["mkdir", "-p", parent])

            # Move to final location with sudo
            self.run_command(["mv", temp_path, remote_path])
        else:
            # Normal SFTP copy (no sudo)
            sftp = self.client.open_sftp()
            try:
                # Create parent directory if needed
                parent = str(Path(remote_path).parent)
                try:
                    sftp.stat(parent)
                except FileNotFoundError:
                    self.run_command(["mkdir", "-p", parent])

                # Copy file
                sftp.put(local_path, remote_path)
            finally:
                sftp.close()

    def close(self) -> None:
        """Close SSH connection."""
        if self.client:
            self.client.close()
