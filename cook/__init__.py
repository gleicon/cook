"""
Cook - Modern configuration management in Python

A simple, powerful configuration management tool focused on:
- Pure Python configs (no YAML/JSON)
- Drift detection and monitoring
- Recording mode to capture manual changes
- AI integration via MCP
"""

__version__ = "0.1.0"

from cook.core.resource import Resource, Plan, Action
from cook.resources.file import File
from cook.resources.pkg import Package
from cook.resources.service import Service
from cook.resources.exec import Exec

__all__ = [
    "Resource",
    "Plan",
    "Action",
    "File",
    "Package",
    "Service",
    "Exec",
]
