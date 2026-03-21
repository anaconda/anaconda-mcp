"""
Suite-wide configuration constants for the stdio_tools suite.
"""

from __future__ import annotations

# Maximum seconds to wait for a single tool call response.
# Same value as http_tools so hang comparisons between transports are apples-to-apples.
TOOL_TIMEOUT: int = 60

# Number of warm-up/test iterations for hang regression tests.
# Set to 15 to stay below the ~20 iteration threshold where the test harness
# (conda run subprocess chain) introduces overhead that causes hangs.
# Claude Desktop works for 28+ iterations; this tests the fix without hitting
# test infrastructure limits.
WARM_ITERATIONS: int = 15
