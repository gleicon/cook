"""
Command parser for recording mode.

Parses shell commands into resource representations.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ParsedResource:
    """Represents a resource parsed from shell commands."""
    type: str  # 'package', 'file', 'service', 'exec'
    data: Dict[str, Any]
    command: str  # Original command


class CommandParser:
    """
    Parse shell commands into resource representations.

    Supports common patterns:
    - apt/dnf/pacman install
    - systemctl start/enable/restart
    - mkdir, touch, chmod, chown
    - cp, mv
    - git clone
    """

    def __init__(self):
        self.patterns = [
            # Package managers
            (re.compile(r'apt(?:-get)?\s+install\s+(?:-y\s+)?(.+)'), self._parse_apt_install),
            (re.compile(r'dnf\s+install\s+(?:-y\s+)?(.+)'), self._parse_dnf_install),
            (re.compile(r'pacman\s+-S\s+(.+)'), self._parse_pacman_install),
            (re.compile(r'brew\s+install\s+(.+)'), self._parse_brew_install),

            # Service management
            (re.compile(r'systemctl\s+(start|stop|restart|reload|enable|disable)\s+(.+)'), self._parse_systemctl),

            # File operations
            (re.compile(r'mkdir\s+(?:-p\s+)?(.+)'), self._parse_mkdir),
            (re.compile(r'touch\s+(.+)'), self._parse_touch),
            (re.compile(r'chmod\s+(\d+)\s+(.+)'), self._parse_chmod),
            (re.compile(r'chown\s+([\w-]+):?([\w-]*)\s+(.+)'), self._parse_chown),

            # Git
            (re.compile(r'git\s+clone\s+(\S+)(?:\s+(\S+))?'), self._parse_git_clone),
        ]

    def parse(self, command: str) -> Optional[ParsedResource]:
        """
        Parse a shell command into a resource.

        Args:
            command: Shell command string

        Returns:
            ParsedResource or None if not recognized
        """
        command = command.strip()
        if not command or command.startswith('#'):
            return None

        # Try each pattern
        for pattern, handler in self.patterns:
            match = pattern.search(command)
            if match:
                return handler(match, command)

        return None

    def parse_history(self, history_lines: List[str]) -> List[ParsedResource]:
        """
        Parse multiple commands from shell history.

        Args:
            history_lines: List of command strings

        Returns:
            List of ParsedResource objects
        """
        resources = []
        for line in history_lines:
            resource = self.parse(line)
            if resource:
                resources.append(resource)
        return resources

    def _parse_apt_install(self, match, command) -> ParsedResource:
        """Parse apt install command."""
        packages_str = match.group(1).strip()
        packages = packages_str.split()

        return ParsedResource(
            type='package',
            data={
                'name': packages[0] if len(packages) == 1 else 'packages',
                'packages': packages if len(packages) > 1 else None,
            },
            command=command
        )

    def _parse_dnf_install(self, match, command) -> ParsedResource:
        """Parse dnf install command."""
        packages_str = match.group(1).strip()
        packages = packages_str.split()

        return ParsedResource(
            type='package',
            data={
                'name': packages[0] if len(packages) == 1 else 'packages',
                'packages': packages if len(packages) > 1 else None,
            },
            command=command
        )

    def _parse_pacman_install(self, match, command) -> ParsedResource:
        """Parse pacman install command."""
        packages_str = match.group(1).strip()
        packages = packages_str.split()

        return ParsedResource(
            type='package',
            data={
                'name': packages[0] if len(packages) == 1 else 'packages',
                'packages': packages if len(packages) > 1 else None,
            },
            command=command
        )

    def _parse_brew_install(self, match, command) -> ParsedResource:
        """Parse brew install command."""
        packages_str = match.group(1).strip()
        packages = packages_str.split()

        return ParsedResource(
            type='package',
            data={
                'name': packages[0] if len(packages) == 1 else 'packages',
                'packages': packages if len(packages) > 1 else None,
            },
            command=command
        )

    def _parse_systemctl(self, match, command) -> ParsedResource:
        """Parse systemctl command."""
        action = match.group(1)
        service = match.group(2).strip()

        # Remove .service suffix if present
        if service.endswith('.service'):
            service = service[:-8]

        data = {
            'name': service,
            'running': action in ['start', 'restart', 'reload'],
            'enabled': action == 'enable',
        }

        return ParsedResource(
            type='service',
            data=data,
            command=command
        )

    def _parse_mkdir(self, match, command) -> ParsedResource:
        """Parse mkdir command."""
        path = match.group(1).strip()

        return ParsedResource(
            type='file',
            data={
                'path': path,
                'ensure': 'directory',
                'mode': 0o755,
            },
            command=command
        )

    def _parse_touch(self, match, command) -> ParsedResource:
        """Parse touch command."""
        path = match.group(1).strip()

        return ParsedResource(
            type='file',
            data={
                'path': path,
                'ensure': 'present',
                'mode': 0o644,
            },
            command=command
        )

    def _parse_chmod(self, match, command) -> ParsedResource:
        """Parse chmod command."""
        mode_str = match.group(1)
        path = match.group(2).strip()

        return ParsedResource(
            type='file',
            data={
                'path': path,
                'mode': int(mode_str, 8),  # Convert octal string to int
            },
            command=command
        )

    def _parse_chown(self, match, command) -> ParsedResource:
        """Parse chown command."""
        owner = match.group(1)
        group = match.group(2) if match.group(2) else None
        path = match.group(3).strip()

        data = {
            'path': path,
            'owner': owner,
        }
        if group:
            data['group'] = group

        return ParsedResource(
            type='file',
            data=data,
            command=command
        )

    def _parse_git_clone(self, match, command) -> ParsedResource:
        """Parse git clone command."""
        repo = match.group(1)
        dest = match.group(2) if match.group(2) else None

        return ParsedResource(
            type='exec',
            data={
                'name': 'git-clone',
                'command': command,
                'creates': dest if dest else repo.split('/')[-1].replace('.git', ''),
            },
            command=command
        )
