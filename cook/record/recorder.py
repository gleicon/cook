"""
Interactive terminal recorder for capturing manual server changes.

Uses PTY wrapper to capture commands and filesystem watcher for file changes.
"""

import json
import os
import pty
import select
import sys
import termios
import tty
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import List, Optional

from cook.logging import get_cook_logger

logger = get_cook_logger(__name__)


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
            shell = os.environ.get("SHELL", "/bin/bash")

        logger.info("Recording session started. Type 'exit' to stop.")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info("")

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

        # Fork with PTY
        pid, master_fd = pty.fork()

        if pid == 0:
            # Child process - replace with the requested shell
            try:
                os.execlp(shell, shell)
            except Exception as e:
                # If exec fails, write error and exit child
                try:
                    sys.stderr.write(f"Failed to exec shell {shell}: {e}\n")
                except Exception:
                    pass
                os._exit(1)
        else:
            # Parent process - set stdin to raw mode so keystrokes forward properly
            stdin_fd = sys.stdin.fileno()
            old_stdin_attrs = None
            try:
                # Save and set raw mode on the real terminal input (not the master FD)
                old_stdin_attrs = termios.tcgetattr(stdin_fd)
                tty.setraw(stdin_fd)
            except Exception:
                # If we can't change terminal mode, continue but ensure no crash
                old_stdin_attrs = None

            try:
                self._io_loop(master_fd)
            except (IOError, OSError):
                pass
            finally:
                # Restore stdin terminal attributes if we changed them
                if old_stdin_attrs is not None:
                    try:
                        termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, old_stdin_attrs)
                    except Exception:
                        pass

                # Close master FD and wait for child to avoid zombies
                try:
                    os.close(master_fd)
                except Exception:
                    pass

                try:
                    os.waitpid(pid, 0)
                except Exception:
                    pass

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
                    text = data.decode("utf-8", errors="ignore")
                    if "\n" in text or "\r" in text:
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
                    text = data.decode("utf-8", errors="ignore")
                    if text == "\r" or text == "\n":
                        if command_line.strip():
                            self._record_command(command_line.strip())
                        command_line = ""
                    elif text == "\x7f":  # Backspace
                        command_line = command_line[:-1]
                    elif not text.startswith("\x1b"):  # Not escape sequence
                        command_line += text
                except:
                    pass

    def _record_command(self, command: str):
        """Record a command execution."""
        # Filter out common noise
        if not command or command in ["ls", "pwd", "clear", "history"]:
            return

        event = CommandEvent(
            timestamp=datetime.now().isoformat(), command=command, cwd=os.getcwd()
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
            watch_paths = ["/etc"]

        self.recording = Recording(
            start_time=datetime.now().isoformat(), watched_paths=watch_paths
        )
        self.terminal_recorder = TerminalRecorder(self.recording)
        self.watcher = None

    def start(self):
        """Start recording session."""
        logger.info("Cook recording session")
        logger.separator("=", 50)

        # Start filesystem watcher if available
        try:
            from cook.record.watcher import FileWatcher

            self.watcher = FileWatcher(self.recording)
            self.watcher.start()
            logger.info(f"Watching: {', '.join(self.recording.watched_paths)}")
        except ImportError:
            logger.warning("Filesystem watcher not available (install watchdog)")

        logger.info("")

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

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"\nRecording saved to {output_file}")
        logger.info(f"Commands captured: {len(self.recording.commands)}")
        logger.info(f"File changes: {len(self.recording.file_changes)}")

    def generate_code(self, output_file: str):
        """
        Generate Cook config from recording.

        Args:
            output_file: Path to save generated .py file
        """
        from cook.record.generator import CodeGenerator
        from cook.record.parser import CommandParser

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
        with open(output_file, "w") as f:
            f.write(code)

        logger.success(f"Generated config saved to {output_file}")
        logger.info(f"Resources extracted: {len(resources)}")
