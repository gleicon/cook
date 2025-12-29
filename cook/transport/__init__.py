"""
Transport layer for local and remote execution.

Provides abstraction for:
- Local command execution
- SSH remote execution
- File transfer (SCP)
"""

from cook.transport.base import Transport
from cook.transport.local import LocalTransport

__all__ = ["Transport", "LocalTransport"]

# SSHTransport will be added when paramiko is installed
try:
    from cook.transport.ssh import SSHTransport
    __all__.append("SSHTransport")
except ImportError:
    pass
