# KI-013 Investigation Status

## BREAKTHROUGH: Root cause identified (2026-03-09)

**KI-013 delays are caused by mcp-compose `timeout` config value.**

| timeout | Per-call delay | Total test time |
|---------|----------------|-----------------|
| 5 | 5.01s | 413s (6:53) |
| 60 | **0.04s** | **172s (2:52)** |

### Mechanism
1. Test has natural gaps between phases
2. If gap > `timeout`, SSE stream disconnects
3. After disconnect, all requests delayed by `timeout` value
4. With timeout=60, gap < 60s, no disconnect, no delays

---

## Completed Tests (Anaconda)

- [x] Telemetry disabled (timeout=5) → 5s delays
- [x] keep_alive=false (timeout=5) → 5s delays
- [x] timeout=60 → **NO delays** (0.04s per call)

## Backups Created

- `config_snapshots/anaconda-mcp-dev-env-export.yml` - Dev environment spec
- `config_snapshots/anaconda-base-packages.txt` - Base environment packages
- `config_snapshots/anaconda-conda-info.txt` - Conda info

---

## Miniconda Comparison - COMPLETED (2026-03-10)

### Results:
- [x] Switched to Miniconda (`/opt/miniconda3`)
- [x] Ran tests with timeout=60
- [x] **Result**: Same behavior as Anaconda (4 pass / 4 fail, 173s)

### Conclusion:
**Miniconda vs Anaconda makes NO difference.** The issue is in mcp-compose/MCP SDK, not conda installation type.

---

## Current Status

### KI-013 (delays): UNDERSTOOD
- **Cause**: `timeout` config value in mcp-compose
- **Trade-off discovered**: Lower timeout = slower but fewer hangs!

| timeout | Delays | Hangs | Result |
|---------|--------|-------|--------|
| 5 | 5s/call | Fewer | 5 pass / 3 fail |
| 60 | None | More | 4 pass / 4 fail |

### KI-011 (hangs): PARTIALLY FIXED
- PR #28 merged in mcp-compose 0.1.11
- HANG-001: ✅ Passes (all 20 iterations)
- HANG-002: ❌ Fails at iteration ~16 (improved from iteration 4)
- **Root cause**: Connection pool corrupts under rapid sequential calls
- **KI-013 delays accidentally help** by acting as cooldown between calls

---

## Workaround

Use `timeout = 60` in mcp-compose config (already set in start-http-server.sh).

## To Report to mcp-compose

File follow-up issue:
- PR #28 improved hang threshold from ~4 to ~16 iterations
- But hang still occurs after ~16 rapid sequential error-triggering calls
- "GET stream disconnected, reconnecting..." appears before hang
- Need further investigation of connection pool management
