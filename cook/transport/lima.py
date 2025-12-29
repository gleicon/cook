"""
Lima VM integration helper.

Provides utilities for auto-detecting Lima VM SSH configuration.
"""

import subprocess
import re
from typing import Optional, Tuple


def get_lima_ssh_config(vm_name: str) -> Tuple[str, int, str, Optional[str]]:
    """
    Get SSH connection details for a Lima VM.

    Args:
        vm_name: Name of the Lima VM

    Returns:
        Tuple of (host, port, user, key_file)

    Raises:
        RuntimeError: If VM not found or not running
        FileNotFoundError: If limactl not installed

    Example:
        host, port, user, key = get_lima_ssh_config("wordpress-demo")
        transport = SSHTransport(host=host, port=port, user=user, key_file=key)
    """
    try:
        # Get SSH config from Lima
        result = subprocess.run(
            ["limactl", "show-ssh", "--format=config", vm_name],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        if "not found" in e.stderr.lower():
            raise RuntimeError(f"Lima VM '{vm_name}' not found or not running")
        raise RuntimeError(f"Failed to get Lima SSH config: {e.stderr}")
    except FileNotFoundError:
        raise FileNotFoundError("limactl not found. Is Lima installed?")

    # Parse SSH config
    config = result.stdout

    # Extract values using regex
    host = "127.0.0.1"  # Lima VMs always use localhost
    port = 22
    user = "root"
    key_file = None

    for line in config.split("\n"):
        line = line.strip()
        if line.startswith("Port "):
            port = int(line.split()[1])
        elif line.startswith("User "):
            user = line.split()[1]
        elif line.startswith("IdentityFile "):
            key_file = line.split()[1].strip('"')

    return host, port, user, key_file


def lima_to_ssh_transport(vm_name: str):
    """
    Create an SSHTransport for a Lima VM.

    Args:
        vm_name: Name of the Lima VM

    Returns:
        SSHTransport instance connected to the VM

    Example:
        transport = lima_to_ssh_transport("wordpress-demo")
        with transport:
            output, code = transport.run_command(["whoami"])
            print(output)
    """
    from cook.transport.ssh import SSHTransport

    host, port, user, key_file = get_lima_ssh_config(vm_name)
    return SSHTransport(host=host, port=port, user=user, key_file=key_file)
