# Start anaconda-mcp HTTP server (Windows version)
# Usage: .\start-http-server.ps1 [port]
#
# Note: Uses `python -m anaconda_mcp` instead of `anaconda-mcp` CLI
# due to PI-001 (missing .exe wrapper on Windows)

param(
    [int]$Port = 8888
)

$DOWNSTREAM_PORT = 4041
$CONFIG_FILE = "$env:TEMP\http-config.toml"

# Get Python from CONDA_PREFIX (active conda env), not PATH
if ($env:CONDA_PREFIX) {
    $PYTHON_PATH = Join-Path $env:CONDA_PREFIX "python.exe"
} else {
    Write-Error "No conda environment is active."
    Write-Host "Run: conda activate anaconda-mcp-rc-py311"
    exit 1
}

if (-not (Test-Path $PYTHON_PATH)) {
    Write-Error "Python not found at $PYTHON_PATH"
    Write-Host "Make sure the conda environment has Python installed."
    exit 1
}

Write-Host "=== Cleanup ===" -ForegroundColor Cyan
# Kill existing anaconda-mcp and environments_mcp processes
Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -eq "python" -and (
        $_.CommandLine -like "*anaconda_mcp*" -or
        $_.CommandLine -like "*environments_mcp*"
    )
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill processes on ports
$netstat = netstat -ano | Select-String ":$Port\s|:$DOWNSTREAM_PORT\s"
$netstat | ForEach-Object {
    if ($_ -match '\s(\d+)$') {
        $pid = $matches[1]
        if ($pid -ne "0") {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
    }
}
Start-Sleep -Seconds 2

Write-Host "=== Creating HTTP config ===" -ForegroundColor Cyan
# Escape backslashes for TOML
$PYTHON_PATH_ESCAPED = $PYTHON_PATH -replace '\\', '\\\\'

$configContent = @"
[composer]
name = "anaconda-mcp"
conflict_resolution = "prefix"
log_level = "INFO"
port = $Port

[transport]
stdio_enabled = false
streamable_http_enabled = true
sse_enabled = false

[[servers.proxied.streamable-http]]
name = "conda"
url = "http://localhost:$DOWNSTREAM_PORT/mcp"
timeout = 30
keep_alive = true
reconnect_on_failure = true
max_reconnect_attempts = 10
health_check_enabled = false
mode = "proxy"
auto_start = true
command = ["$PYTHON_PATH_ESCAPED", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "$DOWNSTREAM_PORT"]
startup_delay = 5

[tool_manager]
conflict_resolution = "prefix"

[api]
enabled = true
path_prefix = "/api/v1"
host = "0.0.0.0"
port = $Port
"@

$configContent | Out-File -FilePath $CONFIG_FILE -Encoding UTF8
Write-Host "Config written to: $CONFIG_FILE" -ForegroundColor Green

Write-Host ""
Write-Host "=== Starting HTTP server on port $Port ===" -ForegroundColor Cyan
Write-Host "Python: $PYTHON_PATH"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

# Use python -m instead of anaconda-mcp CLI (PI-001 workaround)
& $PYTHON_PATH -m anaconda_mcp serve --config $CONFIG_FILE
