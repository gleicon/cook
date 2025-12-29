"""
Recording mode - Capture manual changes and generate Cook configs.

Components:
- Parser: Extract resources from shell commands
- Generator: Convert resources to Python code
- Recorder: PTY-based terminal recorder
- Watcher: Filesystem change monitor (requires watchdog)

Usage:
    cook record start
    # Make changes...
    # Exit shell
    cook record generate recording.json -o config.py
"""

from cook.record.parser import CommandParser, ParsedResource
from cook.record.generator import CodeGenerator
from cook.record.recorder import RecordingSession, Recording

__all__ = [
    'CommandParser',
    'ParsedResource',
    'CodeGenerator',
    'RecordingSession',
    'Recording',
]
