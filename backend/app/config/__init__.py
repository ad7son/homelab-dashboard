"""Platform configuration.

Project-specific settings, including monitored systemd units, live in the
owning project package.
"""

from app.config.version import A7LAS_VERSION

__all__ = ["A7LAS_VERSION"]
