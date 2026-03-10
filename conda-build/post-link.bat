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
        echo The Anaconda MCP Server connects your local conda environments to MCP-compatible AI assistants, enabling them to create, modify, and delete environments and packages on your machine. Install only if you trust the AI assistant you intend to connect and understand it can take real actions on your machine.
        echo By installing you acknowledge:
        echo The AI assistant you connect to this MCP server is an independent third-party model, not a product or service of Anaconda.
        echo Anaconda is NOT responsible for the actions the AI assistant directs within your environment, including unintended changes or deletions.
    )

    echo.
    echo ============================================================
    echo.
) >> "%MSG_FILE%"

EXIT /B 0
