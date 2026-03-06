"""
Suite-wide configuration constants for the stdio_tools suite.
"""

from __future__ import annotations

# Maximum seconds to wait for a single tool call response.
# Same value as http_tools so hang comparisons between transports are apples-to-apples.
TOOL_TIMEOUT: int = 60

# Port for environments_mcp_server in STDIO test runs.
# Deliberately different from the HTTP-test port (4041) so both suites
# can run in the same pytest session without port conflicts.
DOWNSTREAM_PORT: int = 4042

# Number of warm-up/test iterations for hang regression tests.
# Higher than http_tools (40 vs 20) because STDIO process startup
# amortizes well across more iterations.
WARM_ITERATIONS: int = 40
