"""
Simple Cook example - Create a test file.

This is the simplest possible Cook config to verify the system works.

Run with:
    cook plan examples/simple.py
    cook apply examples/simple.py
"""

from cook import File

# Create a simple test file
File("/tmp/cook-test.txt",
     content="Hello from Cook!\n",
     mode=0o644)

File("/tmp/cook-dir",
     ensure="directory",
     mode=0o755)

print("Config loaded successfully")
