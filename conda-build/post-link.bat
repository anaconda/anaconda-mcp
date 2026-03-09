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
        echo Anaconda MCP connects an AI assistant (Claude, by Anthropic^)
        echo to your computing environment. By using this software, you
        echo acknowledge that:
        echo.
        echo   - Claude is developed by Anthropic, not Anaconda.
        echo   - You are solely responsible for the permissions you grant.
        echo   - Anaconda is NOT liable for any actions Claude takes in
        echo     your environment, including unintended changes or deletions.
        echo.
        echo Full EULA: https://docs.anaconda.com/anaconda-mcp/eula
    )

    echo.
    echo ============================================================
    echo.
    echo Please run 'anaconda-mcp' to accept the EULA before first use.
    echo.
) >> "%MSG_FILE%"

EXIT /B 0
