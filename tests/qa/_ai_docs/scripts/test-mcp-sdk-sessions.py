#!/usr/bin/env python3
"""
Minimal test to reproduce the MCP SDK session hang.

This test creates many sequential sessions to an MCP server to see if
the session accumulation causes hangs (like we see with mcp-compose).

Usage:
    # Terminal 1: Start environments_mcp_server
    python -m environments_mcp_server start --transport streamable-http --port 5041

    # Terminal 2: Run this test
    python test-mcp-sdk-sessions.py [iterations] [port]
"""

import asyncio
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_sessions(iterations: int = 30, port: int = 5041):
    """
    Test creating many sequential sessions to an MCP server.

    This mimics what mcp-compose does: creates a new session for each tool call.
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = f"http://localhost:{port}/mcp"
    logger.info(f"Testing {iterations} sequential sessions to {url}")

    passed = 0
    failed_at = 0

    for i in range(1, iterations + 1):
        start_time = time.time()
        logger.info(f"[{i}/{iterations}] Creating session...")

        try:
            async with streamablehttp_client(
                url=url,
                timeout=60.0,
            ) as (read_stream, write_stream, get_session_id):
                session_id = get_session_id() if callable(get_session_id) else "unknown"
                logger.info(f"[{i}/{iterations}] Session ID: {session_id}")

                async with ClientSession(read_stream, write_stream) as session:
                    logger.info(f"[{i}/{iterations}] Initializing...")
                    await session.initialize()

                    logger.info(f"[{i}/{iterations}] Calling install_packages...")
                    result = await session.call_tool(
                        "install_packages", {"environment": "guard-api-test", "packages": ["pyyaml"]}
                    )

                    elapsed = time.time() - start_time
                    logger.info(f"[{i}/{iterations}] SUCCESS in {elapsed:.2f}s")
                    passed += 1

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.error(f"[{i}/{iterations}] TIMEOUT after {elapsed:.2f}s")
            failed_at = i
            break
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[{i}/{iterations}] FAILED after {elapsed:.2f}s: {type(e).__name__}: {e}")
            failed_at = i
            break

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if failed_at > 0:
        print(f"FAILED at iteration {failed_at}")
        print(f"Passed: {passed}/{iterations}")
        print("\nThis confirms the bug is in MCP SDK session handling!")
    else:
        print(f"PASSED: {passed}/{iterations} iterations completed")
        print("\nNo hang detected - bug may be in mcp-compose's proxy layer")

    return failed_at == 0


async def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5041

    success = await test_sessions(iterations, port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
