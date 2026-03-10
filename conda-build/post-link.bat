@echo off
REM post-link.bat — placed next to meta.yaml, conda-build renames it automatically.
REM Output goes to %PREFIX%\.messages.txt per conda conventions.

SET EULA_FILE=%PREFIX%\share\anaconda-mcp\EULA.txt
SET ACCEPTANCE_FLAG=%PREFIX%\share\anaconda-mcp\.eula_accepted
SET MSG_FILE=%PREFIX%\.messages.txt

REM Skip if already accepted (e.g. reinstall/update)
IF EXIST "%ACCEPTANCE_FLAG%" EXIT /B 0

(
    echo.
    echo ============================================================
    echo   ANACONDA MCP - END USER LICENSE AGREEMENT
    echo ============================================================
    echo.

    IF EXIST "%EULA_FILE%" (
        type "%EULA_FILE%"
    ) ELSE (
        echo The Anaconda MCP Server is now installed. When connected to an MCP-compatible AI assistant, it can:
        echo Create, update, and delete conda environments, install, update, and remove packages
        echo Read your current environment state.
        echo These actions occur on your machine based on AI instructions.
        echo Anaconda is not responsible for changes made to your environments, including unintended modifications or deletions.
        echo You can revoke access at any time by stopping or uninstalling the MCP server.
    )

    echo.
    echo ============================================================
    echo.
    echo Please run 'anaconda-mcp' to accept the EULA before first use.
    echo.
) >> "%MSG_FILE%"

EXIT /B 0
