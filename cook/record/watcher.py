"""
Filesystem watcher for recording mode.

Monitors file changes during recording session.
"""

import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
    FileSystemEvent = None

from cook.record.recorder import Recording, FileChangeEvent


class CookFileHandler(FileSystemEventHandler):
    """
    Filesystem event handler for Cook recording.

    Captures file create/modify/delete events.
    """

    def __init__(self, recording: Recording):
        super().__init__()
        self.recording = recording
        self.ignore_patterns = [
            '.swp', '.swx', '.tmp', '~',  # Editor temp files
            '.git/', '__pycache__/', '.pyc',  # VCS and Python
        ]

    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True
        return False

    def on_created(self, event: FileSystemEvent):
        """Handle file creation."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._record_change(event.src_path, 'created')

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._record_change(event.src_path, 'modified')

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion."""
        if event.is_directory or self.should_ignore(event.src_path):
            return

        self._record_change(event.src_path, 'deleted')

    def _record_change(self, path: str, operation: str):
        """Record a file change event."""
        content_hash = None
        mode = None
        owner = None
        group = None

        # Get file metadata if it exists
        if operation != 'deleted' and os.path.exists(path):
            try:
                stat_info = os.stat(path)
                mode = stat_info.st_mode

                # Get owner/group names
                import pwd
                import grp
                try:
                    owner = pwd.getpwuid(stat_info.st_uid).pw_name
                except:
                    owner = str(stat_info.st_uid)

                try:
                    group = grp.getgrgid(stat_info.st_gid).gr_name
                except:
                    group = str(stat_info.st_gid)

                # Hash file content
                if os.path.isfile(path):
                    try:
                        with open(path, 'rb') as f:
                            content_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                    except:
                        pass

            except OSError:
                pass

        event = FileChangeEvent(
            timestamp=datetime.now().isoformat(),
            path=path,
            operation=operation,
            content_hash=content_hash,
            mode=mode,
            owner=owner,
            group=group
        )

        self.recording.file_changes.append(event)


class FileWatcher:
    """
    Filesystem watcher for recording sessions.

    Monitors specified paths for changes.
    """

    def __init__(self, recording: Recording):
        """
        Initialize file watcher.

        Args:
            recording: Recording object to store events
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError(
                "Filesystem watching requires watchdog library. "
                "Install with: pip install watchdog"
            )

        self.recording = recording
        self.observer = Observer()
        self.handler = CookFileHandler(recording)

    def start(self):
        """Start watching filesystem."""
        for path in self.recording.watched_paths:
            if os.path.exists(path):
                self.observer.schedule(self.handler, path, recursive=True)

        self.observer.start()

    def stop(self):
        """Stop watching filesystem."""
        self.observer.stop()
        self.observer.join()
