# KI-013 Test Logs

## Anaconda Tests (2026-03-09)

All tests run on macOS with full Anaconda installation.

### Test A: Telemetry disabled, timeout=5
- `macos_anaconda_telemetry_off_mcp.log` - MCP server logs
- `macos_anaconda_telemetry_off_tcs.log` - Test case output
- **Result**: 5.01s delays, 413s total, 5 passed / 3 failed

### Test B: keep_alive=false, timeout=5
- `macos_anaconda_telemetry_off_keepalive_off_mcp.log`
- `macos_anaconda_telemetry_off_keepalive_off_tcs.log`
- **Result**: 5.01s delays, 413s total, 5 passed / 3 failed
- **Conclusion**: keep_alive not the cause

### Test C: timeout=60 (INVALID - config not updated)
- `macos_anaconda_telemetry_off_timeout_60_mcp.log`
- `macos_anaconda_telemetry_off_timeout_60_tcs.log`
- **Result**: Still 5s delays (script regenerated config)
- **Conclusion**: Discard - test was invalid

### Test D: timeout=60 (VALID - script edited)
- `macos_anaconda_telemetry_off_timeout_60_mcp_2.log`
- `macos_anaconda_telemetry_off_timeout_60_tcs_2.log`
- **Result**: 0.04s per call, 172s total, 4 passed / 4 failed
- **Conclusion**: DELAYS GONE when timeout=60

---

## Miniconda Tests (2026-03-10)

Switched from Anaconda to Miniconda (`/opt/miniconda3`) to test if installation type affects behavior.

### Test E: Miniconda, timeout=60
- `macos_miniconda_mcp.log` - MCP server logs
- `macos_miniconda_tcs.log` - Test case output
- **Result**: 0.03-0.04s per call, 173s total, 4 passed / 4 failed
- **Conclusion**: Same as Anaconda with timeout=60

---

## Summary

| Test | Conda Type | timeout | Per-call | Total | Result |
|------|------------|---------|----------|-------|--------|
| A | Anaconda | 5 | 5.01s | 413s | 5 pass / 3 fail |
| B | Anaconda | 5 | 5.01s | 413s | 5 pass / 3 fail |
| D | Anaconda | 60 | 0.04s | 172s | 4 pass / 4 fail |
| E | Miniconda | 60 | 0.04s | 173s | 4 pass / 4 fail |

## Key Findings

1. **KI-013 (delays)**: Caused by `timeout` config value. With timeout=60, no delays occur.

2. **Miniconda vs Anaconda**: No difference in behavior. The hang issue (KI-011) is in mcp-compose/MCP SDK, not conda.

3. **Trade-off discovered**: Lower timeout causes MORE test passes!
   - `timeout=5`: 5 pass / 3 fail (delays act as cooldown, pool recovers)
   - `timeout=60`: 4 pass / 4 fail (rapid calls, pool corrupts faster)

   The KI-013 delays were accidentally **preventing** KI-011 hangs by slowing down the call rate.

4. **Root cause**: The real issue is mcp-compose connection pool management, not timeout value. Fixing the timeout just exposes the underlying pool corruption bug.
