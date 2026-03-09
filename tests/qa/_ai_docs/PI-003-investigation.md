# PI-003: `anaconda-connector` Downloads Fail — Oversized Telemetry Headers Rejected by S3

**Status**: Root cause confirmed · Workaround available · Bug to file against `conda-anaconda-telemetry`  
**Discovered**: March 2026, Windows QA with full Anaconda installation

---

## Summary

When creating the RC test environment on a machine with a large conda base (full Anaconda install), all three `anaconda-connector` packages fail to download with `HTTP 400 BAD REQUEST`. The conda solver runs correctly, the environment plan resolves, other packages download fine — only `anaconda-connector-*` fails.

The token is valid. The channel is accessible. The failure happens after a successful redirect — on the S3 side — because conda forwards a multi-kilobyte telemetry header to AWS S3, which enforces a hard **8192-byte limit** on request headers.

---

## Failure Flow

```
conda create ...
    │
    ├── Solver resolves plan                          ✓
    ├── repodata.json downloads from all channels     ✓
    ├── ~150 packages download from repo.anaconda.com ✓  (Cloudflare CDN — no header size limit)
    │
    └── anaconda-connector-*.conda
            │
            ▼
        GET conda.anaconda.org/t/<TOKEN>/anaconda-connector/noarch/anaconda-connector-core-0.1.10-pypy_0.conda
            │
            ▼  302 Redirect  ✓  (token is valid)
            │
        GET binstar-cio-packages-prod.s3.amazonaws.com/...?X-Amz-Signature=...
            │
            │  conda carries ALL headers to S3, including:
            │    Anaconda-Telemetry-Packages: defaults/win-64::_anaconda_depends-...
            │    (full base env package list — several KB)
            │
            ▼  400 Bad Request  ✗
            │
        S3: RequestHeaderSectionTooLarge (max 8192 bytes)
            │
            ▼
        conda: CondaHTTPError: HTTP 400 BAD REQUEST
```

---

## Why Only `anaconda-connector`

All other packages in the install plan are served from `repo.anaconda.com` (Cloudflare CDN). Cloudflare accepts large headers without complaint. Only `anaconda-connector-*` comes from `conda.anaconda.org`, which redirects to AWS S3 — and S3 enforces the 8192-byte limit strictly.

---

## Root Cause

The `conda-anaconda-telemetry` plugin (installed as part of the Anaconda distribution) injects several `Anaconda-Telemetry-*` headers into every conda HTTP request. The largest is `Anaconda-Telemetry-Packages`, which contains the full package list of the base environment serialized as a semicolon-separated string.

On a full Anaconda installation this list contains 500+ entries. Each entry looks like:

```
defaults/win-64::anaconda-navigator-2.6.6-py313haa95532_2
```

At ~60–80 characters per entry, 500 entries = **~35,000 bytes** — more than four times S3's limit.

When conda follows the `302` redirect from `conda.anaconda.org` to S3, it carries this header to a host that was never meant to receive it. S3 rejects the request.

---

## Evidence from `conda create -vvv` Log

### Step 1 — Redirect succeeds (token is valid)

```
DEBUG urllib3.connectionpool:_make_request(544):
  https://conda.anaconda.org:443
  "GET /t/<TOKEN>/anaconda-connector/noarch/anaconda-connector-core-0.1.10-pypy_0.conda HTTP/1.1"
  302 None

DEBUG urllib3.connectionpool:_make_request(544):
  https://conda.anaconda.org:443
  "GET /t/<TOKEN>/anaconda-connector/noarch/anaconda-connector-utilities-0.1.10-pypy_0.conda HTTP/1.1"
  302 None

DEBUG urllib3.connectionpool:_make_request(544):
  https://conda.anaconda.org:443
  "GET /t/<TOKEN>/anaconda-connector/noarch/anaconda-connector-conda-0.1.10-pypy_0.conda HTTP/1.1"
  302 None
```

All three packages get a valid redirect. Token confirmed working.

### Step 2 — Conda follows redirect to S3, sends oversized headers

```
>>GET /698304d40a0f659d73244fe9/69a5b991eb5ef7934c3cef9a?...&X-Amz-Signature=... HTTPS
> User-Agent: conda/25.5.1 requests/2.32.3 CPython/3.13.5 Windows/11 ...
> Accept: */*
> Accept-Encoding: gzip, deflate, br, zstd
> Anaconda-Telemetry-Channels: https://conda.anaconda.org/datalayer/win-64;...
> Anaconda-Telemetry-Install: python=3.10;anaconda-mcp=1.0.0.rc.1;...
> Anaconda-Telemetry-Packages: defaults/win-64::_anaconda_depends-2025.06-py313_mkl_2;
    defaults/win-64::aiobotocore-2.19.0-py313haa95532_0;
    defaults/win-64::aiohappyeyeballs-2.4.4-py313haa95532_0;
    ... [500+ more entries] ...
> Anaconda-Telemetry-Sys-Info: conda_build_version:25.5.0;conda_command:create
> Anaconda-Telemetry-Virtual-Packages: __archspec=1=x86_64_v3;__conda=25.5.1=0;__win=10.0.26200=0
> Connection: keep-alive
```

### Step 3 — S3 rejects with header size error

```
<<HTTPS 400 Bad Request
< Content-Type: application/xml
< Server: AmazonS3

<?xml version="1.0" encoding="UTF-8"?>
<Error>
  <Code>RequestHeaderSectionTooLarge</Code>
  <Message>Your request header section exceeds the maximum allowed size.</Message>
  <MaxSizeAllowed>8192</MaxSizeAllowed>
</Error>
```

### Step 4 — Conda surfaces it as HTTP 400

```
conda.CondaMultiError: HTTP 400 BAD REQUEST for url
  <https://conda.anaconda.org/t/an-.../anaconda-connector/noarch/anaconda-connector-core-0.1.10-pypy_0.conda>
```

Note: conda redacts the token in the error message (`<TOKEN>`), but the actual request used the real token and the redirect succeeded.

---

## Trigger Condition — Base Environment Size

The `Anaconda-Telemetry-Packages` header is sized proportionally to the number of packages in the base environment. The bug triggers when the total request header section exceeds 8192 bytes.

| Installation | Base packages | Header size | S3 response |
|---|---|---|---|
| Full Anaconda | ~500+ | >> 8192 bytes | 400 — `RequestHeaderSectionTooLarge` |
| Trimmed conda (Mac QA machine) | ~130 | ~8 KB boundary | No failure observed |
| Miniconda | ~30–50 | << 8192 bytes | 200 — download succeeds |

**This is not an OS issue.** Full Anaconda on Mac would fail identically. Miniconda on Windows would succeed. The confirmed Mac base size is 131 packages (`conda list -n base | wc -l` = 131) — this is why Mac QA testing did not encounter the issue.

---

## Verification — `curl` Confirms Token Is Valid

Direct `curl` of the same URL (without conda's telemetry headers) returns a valid S3 redirect:

```
curl https://conda.anaconda.org/t/an-19ec59a6-f3b4-4d62-a686-a882d9c1f209/anaconda-connector/noarch/anaconda-connector-core-0.1.10-pypy_0.conda

<!doctype html>
<title>Redirecting...</title>
<p>You should be redirected automatically to the target URL:
  <a href="https://binstar-cio-packages-prod.s3.amazonaws.com/...">...</a>
```

The token is valid and the package is accessible. The failure is entirely in the headers conda adds before following the redirect.

---

## What Was Ruled Out

| Hypothesis | Result |
|---|---|
| Token expired / invalid | ✗ Ruled out — `curl` returns valid 302 redirect |
| Conda cache corruption | ✗ Ruled out — same failure after `conda clean --all -y` |
| SSL/TLS issue on Windows | ✗ Ruled out — redirect and response parsing work; error is server-side |
| Windows-specific behavior | ✗ Ruled out — trigger is base env size, not OS |
| Conflicting auth headers | ✗ Ruled out — no `Authorization` header in log; token is URL-embedded only |

---

## Workaround

Disable conda's anonymous usage telemetry before running `conda create`. This stops the `Anaconda-Telemetry-Packages` header from being injected.

**Permanent (until re-enabled):**
```bash
conda config --set anaconda_anon_usage false
conda create ...
```

**One-shot (macOS / Linux):**
```bash
CONDA_ANACONDA_ANON_USAGE=false conda create ...
```

**One-shot (Windows):**
```bat
set CONDA_ANACONDA_ANON_USAGE=false
conda create ...
```

Re-enable after testing if desired:
```bash
conda config --set anaconda_anon_usage true
```

**Better long-term solution**: Use Miniconda instead of full Anaconda. See [CONDA_SETUP.md](./CONDA_SETUP.md).

---

## Bug to File

**Component**: `conda-anaconda-telemetry`  
**Title**: Telemetry headers forwarded to S3 redirect targets, exceeding AWS 8192-byte header limit

**Description**: The plugin injects `Anaconda-Telemetry-*` headers (including a full base env package list) into all conda HTTP requests. When conda follows a redirect from `conda.anaconda.org` to `s3.amazonaws.com`, these headers are carried to S3. AWS S3 enforces a strict 8192-byte request header section limit and rejects the request with `RequestHeaderSectionTooLarge`.

**Fix**: Strip `Anaconda-Telemetry-*` headers before sending requests to non-Anaconda domains (any domain not under `anaconda.org`, `anaconda.com`, or `repo.anaconda.com`). These headers are intended for Anaconda analytics endpoints only — forwarding them to third-party CDNs and object storage is unintentional and causes failures.

**Additional concern**: The `Anaconda-Telemetry-Packages` header (full installed package list) is being sent to AWS S3 presigned URLs unintentionally. This may be a privacy/data-leakage concern worth reviewing.
