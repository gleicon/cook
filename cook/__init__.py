__version__ = "0.1.0"

from cook.core import Resource, Plan, Action
from cook.resources.file import File
from cook.resources.pkg import Package
from cook.resources.service import Service
from cook.resources.exec import Exec
from cook.logging import get_logger, get_cook_logger, setup_logging

"""
Foundations of Cook Workflows:
    Resource is a unit of configuration that represents a desired state of a system.
    Plan is a collection of resources that represent a desired state of a system.
    Action is a unit of work that can be performed on a resource.
    File is a unit of configuration that represents a desired state of a file.
    Package is a unit of configuration that represents a desired state of a package.
    Service is a unit of configuration that represents a desired state of a service.
    Exec is a unit of configuration that represents a desired state of an executable.
"""

__all__ = [
    "Resource",
    "Plan",
    "Action",
    "File",
    "Package",
    "Service",
    "Exec",
    "get_logger",
    "get_cook_logger",
    "setup_logging",
]
