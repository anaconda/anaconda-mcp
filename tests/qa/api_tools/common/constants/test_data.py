"""
Reusable test data constants for the api_tools suite.
"""

from __future__ import annotations

# Ephemeral conda environment created and destroyed per test module.
ENV_NAME = "guard-api-test"

# Ephemeral conda environment used for removal operation tests (KI-003).
REMOVABLE_ENV_NAME = "guard-env-remove-test"

# Package name guaranteed not to exist in any conda channel.
NONEXISTENT_PKG = "nonexistent-package-xyz123"

# Absolute path guaranteed not to be a real conda environment prefix.
# Used to trigger "environment not found" error responses from tools that
# accept a prefix argument, without creating or removing any real environment.
NONEXISTENT_ENV_PREFIX = "/tmp/nonexistent-conda-env-xyz123"
