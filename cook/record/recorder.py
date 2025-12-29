"""
Interactive terminal recorder for capturing manual server changes.

Uses PTY wrapper to capture commands and filesystem watcher for file changes.
"""

import os
import sys
import pty
import select
import termios
import tty
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class CommandEvent:
    """Recorded shell command."""
    timestamp: str
    command: str
    cwd: str


@dataclass
class FileChangeEvent:
    """Recorded file system change."""
    timestamp: str
    path: str
    operation: str  # 'created', 'modified', 'deleted'
    content_hash: Optional[str] = None
    mode: Optional[int] = None
    owner: Optional[str] = None
    group: Optional[str] = None


@dataclass
class Recording:
    """Complete recording session."""
    start_time: str
    end_time: Optional[str] = None
    commands: List[CommandEvent] = field(default_factory=list)
    file_changes: List[FileChangeEvent] = field(default_factory=list)
    watched_paths: List[str] = field(default_factory=list)


class TerminalRecorder:
    """
    PTY-based terminal recorder.

    Captures terminal session by wrapping shell in a PTY.
    Records all commands executed.
    """

    def __init__(self, recording: Recording):
        self.recording = recording
        self.command_buffer = []
        self.current_command = ""

    def start(self, shell: str = None):
        """
        Start recording terminal session.

        Args:
            shell: Shell to use (default: $SHELL or /bin/bash)
        """
        if shell is None:
            shell = os.environ.get('SHELL', '/bin/bash')

        print(f"Recording session started. Type 'exit' to stop.")
        print(f"Working directory: {os.getcwd()}")
        print()

        # Save terminal attributes
        old_tty = termios.tcgetattr(sys.stdin)

        try:
            # Create PTY
            self._run_pty(shell)
        finally:
            # Restore terminal
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_tty)

    def _run_pty(self, shell: str):
        """Run shell in PTY and capture I/O."""

        def read(fd):
            """Read from file descriptor."""
            try:
                return os.read(fd, 1024)
            except OSError:
                return b''

        # Fork with PTY
        pid, master_fd = pty.fork()

        if pid == 0:
            # Child process - run shell
            os.execlp(shell, shell)
        else:
            # Parent process - capture I/O
            try:
                mode = tty.tcgetattr(master_fd)
                tty.setraw(master_fd)
                tty.tcsetattr(master_fd, tty.TCSAFLUSH, mode)
            except tty.error:
                pass

            try:
                self._io_loop(master_fd)
            except (IOError, OSError):
                pass

            # Wait for shell to exit
            os.waitpid(pid, 0)

    def _io_loop(self, master_fd):
        """Main I/O loop for PTY."""
        command_line = ""

        while True:
            # Wait for I/O
            r, w, e = select.select([master_fd, sys.stdin], [], [])

            if master_fd in r:
                # Read from shell
                data = os.read(master_fd, 1024)
                if not data:
                    break

                # Write to terminal
                os.write(sys.stdout.fileno(), data)

                # Parse for command completion (naive: look for newline)
                try:
                    text = data.decode('utf-8', errors='ignore')
                    if '\n' in text or '\r' in text:
                        if command_line.strip():
                            self._record_command(command_line.strip())
                        command_line = ""
                    else:
                        command_line += text
                except:
                    pass

            if sys.stdin in r:
                # Read from keyboard
                data = os.read(sys.stdin.fileno(), 1024)
                if not data:
                    break

                # Write to shell
                os.write(master_fd, data)

                # Track command being typed
                try:
                    text = data.decode('utf-8', errors='ignore')
                    if text == '\r' or text == '\n':
                        if command_line.strip():
                            self._record_command(command_line.strip())
                        command_line = ""
                    elif text == '\x7f':  # Backspace
                        command_line = command_line[:-1]
                    elif not text.startswith('\x1b'):  # Not escape sequence
                        command_line += text
                except:
                    pass

    def _record_command(self, command: str):
        """Record a command execution."""
        # Filter out common noise
        if not command or command in ['ls', 'pwd', 'clear', 'history']:
            return

        event = CommandEvent(
            timestamp=datetime.now().isoformat(),
            command=command,
            cwd=os.getcwd()
        )
        self.recording.commands.append(event)


class RecordingSession:
    """
    Complete recording session manager.

    Manages PTY recorder and filesystem watcher together.
    """

    def __init__(self, watch_paths: List[str] = None):
        """
        Initialize recording session.

        Args:
            watch_paths: Paths to watch for changes (default: ['/etc'])
        """
        if watch_paths is None:
            watch_paths = ['/etc']

        self.recording = Recording(
            start_time=datetime.now().isoformat(),
            watched_paths=watch_paths
        )
        self.terminal_recorder = TerminalRecorder(self.recording)
        self.watcher = None

    def start(self):
        """Start recording session."""
        print("Cook recording session")
        print("=" * 50)

        # Start filesystem watcher if available
        try:
            from cook.record.watcher import FileWatcher
            self.watcher = FileWatcher(self.recording)
            self.watcher.start()
            print(f"Watching: {', '.join(self.recording.watched_paths)}")
        except ImportError:
            print("Filesystem watcher not available (install watchdog)")

        print()

        # Start terminal recorder
        self.terminal_recorder.start()

        # Stop watcher
        if self.watcher:
            self.watcher.stop()

        # Mark end time
        self.recording.end_time = datetime.now().isoformat()

    def save(self, output_file: str):
        """
        Save recording to file.

        Args:
            output_file: Path to save recording JSON
        """
        data = asdict(self.recording)

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\nRecording saved to {output_file}")
        print(f"Commands captured: {len(self.recording.commands)}")
        print(f"File changes: {len(self.recording.file_changes)}")

    def generate_code(self, output_file: str):
        """
        Generate Cook config from recording.

        Args:
            output_file: Path to save generated .py file
        """
        from cook.record.parser import CommandParser
        from cook.record.generator import CodeGenerator

        # Parse commands
        parser = CommandParser()
        resources = []

        for cmd_event in self.recording.commands:
            resource = parser.parse(cmd_event.command)
            if resource:
                resources.append(resource)

        # Generate code
        generator = CodeGenerator()
        code = generator.generate(resources)

        # Add file changes as comments
        if self.recording.file_changes:
            code += "\n# File changes detected:\n"
            for change in self.recording.file_changes:
                code += f"# {change.operation}: {change.path}\n"

        # Save
        with open(output_file, 'w') as f:
            f.write(code)

        print(f"\nGenerated config saved to {output_file}")
        print(f"Resources extracted: {len(resources)}")
