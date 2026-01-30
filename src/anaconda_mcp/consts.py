"""
Constants for Anaconda MCP.

This module defines constants used throughout the Anaconda MCP package.
"""

from enum import Enum


class OSSystems(Enum):
    """Supported operating systems."""

    WINDOWS = "Windows"
    LINUX = "Linux"
    DARWIN = "Darwin"  # macOS

    @classmethod
    def current(cls) -> "OSSystems":
        """
        Get the current operating system.

        Returns:
            OSSystems enum value for the current platform

        Raises:
            RuntimeError: If the OS is not supported
        """
        import platform

        system = platform.system()
        for os_system in cls:
            if os_system.value == system:
                return os_system
        raise RuntimeError(f"Unsupported operating system: {system}")


class TransportTypes(Enum):
    """Supported MCP transport types."""

    STDIO = "stdio"
    STREAMABLE_HTTP = "streamable-http"
