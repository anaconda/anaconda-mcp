@echo off
REM Start anaconda-mcp HTTP server (Windows CMD/Anaconda Prompt version)
REM Usage: start-http-server.cmd [port]
REM
REM Note: Uses `python -m anaconda_mcp` instead of `anaconda-mcp` CLI
REM due to PI-001 (missing .exe wrapper on Windows)

setlocal enabledelayedexpansion

set PORT=%1
if "%PORT%"=="" set PORT=8888
set DOWNSTREAM_PORT=4041
set CONFIG_FILE=%TEMP%\http-config.toml

REM Get Python from CONDA_PREFIX (active conda env), not PATH
if defined CONDA_PREFIX (
    set "PYTHON_PATH=%CONDA_PREFIX%\python.exe"
) else (
    echo ERROR: No conda environment is active.
    echo Run: conda activate anaconda-mcp-rc-py311
    exit /b 1
)

if not exist "%PYTHON_PATH%" (
    echo ERROR: Python not found at %PYTHON_PATH%
    echo Make sure the conda environment has Python installed.
    exit /b 1
)

echo === Cleanup ===
REM Kill processes on ports (best effort)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% :%DOWNSTREAM_PORT%"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo === Creating HTTP config ===

REM Escape backslashes for TOML
set "PYTHON_ESCAPED=%PYTHON_PATH:\=\\%"

(
echo [composer]
echo name = "anaconda-mcp"
echo conflict_resolution = "prefix"
echo log_level = "INFO"
echo port = %PORT%
echo.
echo [transport]
echo stdio_enabled = false
echo streamable_http_enabled = true
echo sse_enabled = false
echo.
echo [[servers.proxied.streamable-http]]
echo name = "conda"
echo url = "http://localhost:%DOWNSTREAM_PORT%/mcp"
echo timeout = 30
echo keep_alive = true
echo reconnect_on_failure = true
echo max_reconnect_attempts = 10
echo health_check_enabled = false
echo mode = "proxy"
echo auto_start = true
echo command = ["%PYTHON_ESCAPED%", "-m", "environments_mcp_server", "start", "--transport", "streamable-http", "--port", "%DOWNSTREAM_PORT%"]
echo startup_delay = 5
echo.
echo [tool_manager]
echo conflict_resolution = "prefix"
echo.
echo [api]
echo enabled = true
echo path_prefix = "/api/v1"
echo host = "0.0.0.0"
echo port = %PORT%
) > "%CONFIG_FILE%"

echo Config written to: %CONFIG_FILE%
echo.
echo === Starting HTTP server on port %PORT% ===
echo Python: %PYTHON_PATH%
echo Press Ctrl+C to stop
echo.

REM Use python -m instead of anaconda-mcp CLI (PI-001 workaround)
python -m anaconda_mcp serve --config "%CONFIG_FILE%"
