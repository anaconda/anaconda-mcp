"""
Reusable test data constants for the api_tools suite.
"""

from __future__ import annotations

# Ephemeral conda environment created and destroyed per test module.
ENV_NAME = "guard-api-test"

# Package name guaranteed not to exist in any conda channel.
NONEXISTENT_PKG = "nonexistent-package-xyz123"
