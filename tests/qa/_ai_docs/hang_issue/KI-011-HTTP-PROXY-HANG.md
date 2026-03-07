# KI-011: Technical Investigation — mcp-compose Proxy Hang

**Status**: Root cause confirmed, fix plan ready
**Component**: `mcp-compose` 0.1.10

---

## Stack

```mermaid
graph LR
    A["AI Client<br/>(Cursor / Claude Code / Claude Desktop)"]
    B["mcp-compose<br/>:8888"]
    C["environments_mcp_server<br/>:4041"]

    A -- "Streamable HTTP<br/>or STDIO" --> B
    B -- "Streamable HTTP" --> C
```

The external transport (client → mcp-compose) can be HTTP or STDIO.
The internal transport (mcp-compose → environments_mcp_server) is always
Streamable HTTP, regardless of how the external client connects.

---

## Log Analysis

Server logs at port 4041 revealed two distinct request patterns:

**Normal call** — 6 requests:

```
POST /mcp  200 OK       create session
POST /mcp  202 Accepted initialize
GET  /mcp  200 OK       open SSE stream
POST /mcp  202 Accepted tools/call  ← result arrives via SSE
POST /mcp  200 OK       close session
DELETE /mcp 200 OK      delete session
```

**Hanging call** — 4 requests, no DELETE:

```
POST /mcp  200 OK       create session
GET  /mcp  200 OK       open SSE stream  ⚠️ before initialize
POST /mcp  202 Accepted initialize
POST /mcp  200 OK       tools/call       ⚠️ result inline in body, not via SSE
[no close, no DELETE — session abandoned]
```

Two differences from the normal pattern:

1. The SSE GET stream was opened **before** the initialize POST completed
2. `tools/call` returned **HTTP 200 OK** with the result inline instead of 202 Accepted
   with the result delivered asynchronously via SSE

`environments_mcp_server` responded correctly in both cases. The result was present in
the `tools/call` POST body. The proxy did not forward it.

---

## Protocol Flow

### Normal

```mermaid
sequenceDiagram
    participant C as Client
    participant P as mcp-compose :8888
    participant B as environments_mcp_server :4041

    C->>P: POST /mcp  tools/call
    activate P
    P->>B: POST  create session  → 200 OK
    P->>B: POST  initialize      → 202 Accepted
    P->>B: GET   open SSE stream → 200 OK
    P->>B: POST  tools/call      → 202 Accepted
    B-->>P: result on SSE stream
    P->>B: POST  close session   → 200 OK
    P->>B: DELETE                → 200 OK
    P-->>C: 200 OK (result forwarded)
    deactivate P
```

### Hanging

```mermaid
sequenceDiagram
    participant C as Client
    participant P as mcp-compose :8888
    participant B as environments_mcp_server :4041

    C->>P: POST /mcp  tools/call
    activate P
    P->>B: POST  create session  → 200 OK
    P->>B: GET   open SSE stream → 200 OK  ⚠️ before initialize
    P->>B: POST  initialize      → 202 Accepted
    P->>B: POST  tools/call      → 200 OK  ⚠️ result inline
    Note over P: result dropped — proxy waits on SSE stream
    Note over P: session abandoned — no close, no DELETE
    Note over C: connection held open with SSE keepalives
    Note over C: hangs indefinitely
    deactivate P
```

---

## Automated Testing

### Why a single execution was not enough

Running a single error-triggering call consistently returned `is_error: true` in under
1 second. The race requires the internal HTTP connection pool to reach a specific state.

```mermaid
graph TD
    A["Each tool call opens a new HTTP session to :4041<br/>create → initialize → SSE → call → close → DELETE"]
    B["Under rapid sequential calls, previous connections<br/>are not fully released before the next session starts"]
    C{"Pool threshold<br/>reached?"}
    D["Call completes normally<br/>pool connection retained"]
    E["GET stream opens before initialize<br/>→ race triggered → hang ✗"]

    A --> B --> C
    C -- "No — HTTP: calls 1–3 / STDIO: calls 1–15" --> D --> C
    C -- "Yes — HTTP: call 4 / STDIO: call 16" --> E
```

STDIO adds serialization latency through the stdin/stdout pipe, slowing the rate at
which pool state accumulates — pushing the threshold from call 4 to call 16.

### Warmup approach

Two test suites cover the two upstream transports — see their READMEs for execution
instructions:

| Suite | Transport | README |
|---|---|---|
| `tests/qa/http_tools/test_guard_proxy_error_hang.py` | Streamable HTTP | [http_tools/README.md](../../http_tools/README.md) |
| `tests/qa/stdio_tools/test_guard_proxy_error_hang_stdio.py` | STDIO | [stdio_tools/README.md](../../stdio_tools/README.md) |

Each test calls the same error-triggering tool 20 times in rapid succession. This
accumulates session state and consistently triggers the race condition:

| Test | Tool | Iterations | Result | Hangs at |
|---|---|---|---|---|
| HANG-001 | `conda_remove_environment` error path | 20 | **PASS** | — |
| HANG-002 | `conda_install_packages` error path | 20 | **FAIL** | iteration **4** |
| HANG-003 | 20 × warm-up + 20 × (error + health check) | 60 | **FAIL** | health step **20** |

HANG-002 triggers at exactly iteration 4 across all runs — the internal connection pool
reaches a state that triggers the race at a fixed call count.

HANG-003 exposes a second failure mode: the proxy can corrupt its state while forwarding
an error response, causing the immediately following healthy call to hang — even when
the error call itself returned normally. This matches the production scenario where a
long session eventually stops responding after an error.

---

## STDIO Transport Test

To determine whether the hang is gated on the HTTP upstream path or lives in
`mcp-compose`'s internal proxy logic, a STDIO test suite was created with the
following architecture:

```mermaid
graph LR
    T["test process"]
    P["mcp-compose<br/>(STDIO mode)"]
    B["environments_mcp_server<br/>:4042"]

    T -- "stdin / stdout" --> P
    P -- "Streamable HTTP" --> B
```

The internal proxy path (mcp-compose → environments_mcp_server) is identical to the
HTTP tests. Only the upstream transport differs.

| Test | Tool | Iterations | Result | Hangs at |
|---|---|---|---|---|
| STDIO-HANG-001 | `conda_remove_environment` error path | 20 | **PASS** | — |
| STDIO-HANG-002 | `conda_install_packages` error path | 20 | **FAIL** | iteration **16** |
| STDIO-HANG-003 | 20 × warm-up + 20 × (error + health check) | 60 | **FAIL** | health step **20** |

The same hang was reproduced over STDIO. The upstream transport shifts the iteration
at which the race triggers (4 over HTTP, 16 over STDIO) but does not prevent it.
The bug is in `mcp-compose`'s internal HTTP connection pool, not in the upstream
transport handler.

**Additional finding**: over STDIO, `mcp-compose` encodes a tool error with
`isError: false` at the outer JSON-RPC level (the error payload is inside
`content[0].text`). Over HTTP the same error has `isError: true`. This is a separate,
lower-severity serialization issue unrelated to KI-011.

---

## Root Cause

`mcp-compose` creates a new Streamable HTTP session to `environments_mcp_server` for
each tool call. The expected session lifecycle is:
**create → initialize → open SSE stream → call tool → close → DELETE**

Under race conditions the SSE GET stream is opened before initialize completes. When
`tools/call` is then sent, `environments_mcp_server` returns the result **inline in
the POST response body** (HTTP 200 OK) rather than via the SSE stream. `mcp-compose`
is only listening on the SSE stream and does not read the inline body — the result is
silently dropped.

**Why errors specifically trigger the inline path**:

```mermaid
flowchart TD
    A["tool handler called"]
    A --> B{"awaits any async<br/>operation before returning?"}

    B -- "No — error path<br/>exception caught immediately" --> C["result available<br/>before event loop yields"]
    B -- "Yes — success path<br/>await conda.install(...) etc." --> D["result available<br/>after async I/O completes"]

    C --> E["FastMCP → 200 OK<br/>result inline in POST body"]
    D --> F["FastMCP → 202 Accepted<br/>result delivered via SSE"]

    E --> G["⚠️ mcp-compose: GET SSE stream<br/>cleanup hangs up to 5 min<br/>→ HANG"]
    F --> H["✓ mcp-compose reads result<br/>from SSE → OK"]
```

The session is abandoned without close or DELETE. The connection pool slot it occupies
is never released. All subsequent calls to port 4041 — regardless of upstream session
— block on this stuck slot, making the corruption process-wide.

---

## Ecosystem Context

The same class of bug — Streamable HTTP client locks up, corrupts the connection pool,
and makes all subsequent calls hang process-wide — is widely reported across the MCP
Python ecosystem. None of the issues below describes exactly KI-011, but they confirm
that the GET stream lifecycle race is a systemic weakness in the MCP SDK.

### Related issues

| Issue | Project | Root cause stated | Relationship to KI-011 |
|---|---|---|---|
| [python-sdk #1941](https://github.com/modelcontextprotocol/python-sdk/issues/1941) | MCP Python SDK | GET stream task fails silently → POST SSE response waits for dead task indefinitely | Closest analogue — identical race around GET stream timing |
| [python-sdk #1811](https://github.com/modelcontextprotocol/python-sdk/issues/1811) | MCP Python SDK | `read_stream_writer` left open after SSE disconnect → `receive()` hangs | Same stuck-stream consequence |
| [python-sdk #680](https://github.com/modelcontextprotocol/python-sdk/issues/680) | MCP Python SDK | Server callback response never reaches server → call hangs forever | Same hang pattern, different trigger (fixed in 2025) |
| [openai-agents #1288](https://github.com/openai/openai-agents-python/issues/1288) | OpenAI Agents | Failed connection corrupts anyio cancel scope → all subsequent `await` calls cancelled process-wide | **Identical consequence** — process-wide corruption after one bad call |

### Timing observation confirms the race

The author of python-sdk #1941 noted:

> *"I tried with and without a debugger, and noticed that with a debugger attached,
> the timing overhead masks the race condition and operations complete successfully."*

This is the same character as KI-011: the hang is deterministic under load (fixed call
count: 4 over HTTP, 16 over STDIO) but disappears when execution slows down. Both are
pool-state races, not logic errors.

### What makes KI-011 distinct

All found issues diagnose the problem at the **MCP SDK client** level
(`streamablehttp_client`, `handle_get_stream` task). None identifies the specific
combination that drives KI-011:

1. `mcp-compose` using the **deprecated `streamablehttp_client`** — which silently
   injects a 5-minute SSE read timeout regardless of the configured `timeout` value.
2. The server-side trigger: tool handlers that return **synchronously** cause FastMCP
   to serve the result inline (200 OK), which is the event that activates the broken
   cleanup path in the deprecated client.

The `asyncio.sleep(0)` workaround (server-side, one line per handler) has not been
published by any other project in this context. It is a canonical Python asyncio
technique and is safe, but it is novel as an MCP tool handler mitigation and must be
reverted once the upstream fix ships.

---

## Fix Plan

**All three fixes are required for a complete resolution.** 
- Fix 1 and Fix 2 address the root cause in `mcp-compose` (upstream, not owned by this team). 
- Fix 3 is independent defensive hardening in `environments_mcp_server` (this team's repo). 
- While Fix 1 + Fix 2 are pending upstream, the **Workaround** below can be shipped immediately.

### Fix 1 — Switch from deprecated `streamablehttp_client` to `streamable_http_client` in `mcp-compose`

**Repo**: `mcp-compose` (upstream — file at https://github.com/datalayer/mcp-compose/issues)

`cli.py` uses the deprecated `streamablehttp_client` for every proxied tool call.
The deprecated function silently adds a **5-minute SSE read timeout** (`sse_read_timeout=300s`),
independent of the 30-second `timeout` argument passed by `mcp-compose`. This is why
hangs last minutes, not seconds. The replacement non-deprecated API does not carry this
default:

```python
# mcp_compose/cli.py — proposed change
# Before:
from mcp.client.streamable_http import streamablehttp_client   # deprecated, adds sse_read_timeout=300s
# After:
from mcp.client.streamable_http import streamable_http_client  # current API, no hidden timeout
```

The proxy must also handle both response paths for `tools/call`:

- **202 Accepted** → result arrives asynchronously on SSE stream (currently handled)
- **200 OK** → result is inline in the POST response body (currently causes the hang)

### Fix 2 — Bound each proxied call with `asyncio.timeout` in `mcp-compose`

**Repo**: `mcp-compose` (upstream)

Switching the API (Fix 1) removes the hidden 5-minute default, but a defensive per-call
timeout prevents any future regression regardless of SDK internals or downstream
misbehaviour:

```python
# mcp_compose/cli.py — proposed change
async def streamable_http_tool_proxy(**kwargs):
    async with asyncio.timeout(float(http_config.timeout)):   # hard deadline per call
        async with streamable_http_client(url=http_config.url, ...) as (r, w, _):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.call_tool(original_tool_name, kwargs)
                ...
```

### Fix 3 — Timeouts on conda operations in `environments_mcp_server`

**Repo**: `environments-mcp-server` (owned by this team).

`environments_mcp_server` delegates all real conda work to the `anaconda_connector_conda`
async library (`await conda.install(...)`, `await conda.remove_environment(...)`, etc.).
There are no timeouts on these awaited calls, so a hung conda operation keeps the tool
handler suspended indefinitely, holding the FastMCP SSE stream open forever. Wrap each
call with `asyncio.wait_for`:

```python
try:
    result = await asyncio.wait_for(
        conda.install(...),
        timeout=120,
    )
except asyncio.TimeoutError:
    return ServerToolResult(
        is_error=True,
        error_description="conda operation timed out after 120 seconds.",
    ).model_dump()
```

Apply the same pattern to `conda.remove_environment(...)`, `conda.create(...)`, and
`conda.remove(...)` in the corresponding tool files.

A secondary concern: `utils/conda.py` calls `subprocess.check_output(["conda", "info",
"--json"])` synchronously without a `timeout=` argument. This runs only at startup
(conda discovery), but should also be hardened:

```python
subprocess.check_output(["conda", "info", "--json"], text=True, timeout=30)
```

---

## Workaround — Ship now while Fix 1 + Fix 2 are pending upstream

**Repo**: `environments-mcp-server` (owned by this team).

The hang is triggered exclusively because error-path handlers return *synchronously*
(no `await` before returning), causing FastMCP to serve the result inline via 200 OK.
`mcp-compose` then fails to clean up the GET SSE stream within the 5-minute window.

Adding `await asyncio.sleep(0)` as the **first line** of every tool handler forces a
yield to the event loop before any work begins. FastMCP observes that the result is not
yet available and always uses the 202 Accepted + SSE path — the path `mcp-compose`
handles correctly. The race condition still fires internally but stops mattering.

```mermaid
sequenceDiagram
    participant P as mcp-compose
    participant F as FastMCP
    participant H as tool handler

    Note over P,H: Without workaround
    P->>F: POST tools/call
    F->>H: call handler()
    H-->>F: return immediately (error, no await)
    F-->>P: 200 OK — result inline
    Note over P: GET SSE stream cleanup hangs → HANG

    Note over P,H: With workaround — await asyncio.sleep(0)
    P->>F: POST tools/call
    F->>H: call handler()
    H->>H: await asyncio.sleep(0)  ← yields to event loop
    H-->>F: return result
    F-->>P: 202 Accepted
    F-)P: result via SSE stream
    Note over P: normal SSE path → OK
```

```python
# environments_mcp_server/tools/environments/install_packages.py
@register_tool
async def install_packages(prefix: str, packages: list[str]) -> dict:
    await asyncio.sleep(0)  # workaround: force FastMCP onto 202+SSE path (KI-011)
    try:
        ...
```

Apply to every tool handler (`install_packages`, `remove_packages`,
`remove_environment`, `create_environment`, `list_environments`,
`list_environment_packages`).

This workaround couples `environments_mcp_server` to `mcp-compose`'s broken
assumption and must be reverted once Fix 1 + Fix 2 ship in a `mcp-compose` release.
Mark each added line with a `# workaround KI-011` comment to make the revert obvious.

### Expected outcome (original expectation)

| Symptom | Before | After Fix 1+2 | After Workaround |
|---|---|---|---|
| Hang on error-path tool call | ✓ | ✗ | ✗ |
| Process-wide pool corruption | ✓ | ✗ | ✗ |
| New chat session recovers | ✗ | ✓ | ✓ |
| HANG-002 / STDIO-HANG-002 tests | FAIL | PASS | PASS |

### ⚠️ Actual outcome (tested 2026-03-07)

**The proposed fixes do NOT fully resolve the issue.** Testing revealed the root cause
is deeper than initially analyzed — it's in the MCP SDK's httpx connection pool
management, not just the 5-minute SSE timeout.

| Configuration | Hang iteration | Improvement |
|---------------|----------------|-------------|
| No workaround | 4/20 | baseline |
| `asyncio.sleep(0.1)` in handlers | 18/20 | **4× better** |
| + `sse_read_timeout=30` | 18/20 | no additional improvement |
| + `asyncio.timeout()` wrapper | 18/20 | no additional improvement |
| Switch to `streamable_http_client` | **API incompatible** | cannot test |

The non-deprecated `streamable_http_client` has a different API signature and is not
a drop-in replacement. See [GITHUB-ISSUE-MCP-COMPOSE-PROXY-HANG.md](./GITHUB-ISSUE-MCP-COMPOSE-PROXY-HANG.md)
for full testing details.

**Recommendation**: Apply the `asyncio.sleep(0.1)` workaround for partial mitigation
while monitoring upstream MCP Python SDK for connection pool fixes.

---

## Regression Tests

```
tests/qa/http_tools/test_guard_proxy_error_hang.py      # HTTP transport
tests/qa/stdio_tools/test_guard_proxy_error_hang_stdio.py  # STDIO transport
```

After the fix, all six tests (HANG-001/002/003 and STDIO-HANG-001/002/003) should pass.
