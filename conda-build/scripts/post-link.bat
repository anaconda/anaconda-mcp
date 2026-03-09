@echo off
REM post-link.bat — runs automatically after `conda install anaconda-mcp` on Windows
REM Displays the EULA and requires user acceptance.

SET EULA_FILE=%PREFIX%\share\anaconda-mcp\EULA.txt
SET ACCEPTANCE_FLAG=%PREFIX%\share\anaconda-mcp\.eula_accepted

REM Skip if already accepted (e.g. reinstall/update)
IF EXIST "%ACCEPTANCE_FLAG%" EXIT /B 0

echo.
echo ============================================================
echo   ANACONDA MCP - END USER LICENSE AGREEMENT
echo ============================================================
echo.

IF EXIST "%EULA_FILE%" (
    type "%EULA_FILE%"
) ELSE (
    echo IMPORTANT NOTICE:
    echo.
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

REM Detect non-interactive (CI / --yes) by checking if stdin is a console
powershell -Command "if ([Console]::IsInputRedirected) { exit 0 } else { exit 1 }" >NUL 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo [WARNING] Non-interactive install detected.
    echo By proceeding, you are deemed to have accepted the EULA above.
    echo Full EULA: https://docs.anaconda.com/anaconda-mcp/eula
    echo.
    IF NOT EXIST "%PREFIX%\share\anaconda-mcp" MKDIR "%PREFIX%\share\anaconda-mcp"
    echo accepted-non-interactive > "%ACCEPTANCE_FLAG%"
    EXIT /B 0
)

SET /P REPLY=Do you accept the terms of this End User License Agreement? [yes/no]:

echo.
IF /I "%REPLY%"=="yes" GOTO ACCEPT
IF /I "%REPLY%"=="y"   GOTO ACCEPT

echo [ABORTED] You must accept the EULA to use Anaconda MCP.
echo To uninstall: conda remove anaconda-mcp
echo.
EXIT /B 1

:ACCEPT
IF NOT EXIST "%PREFIX%\share\anaconda-mcp" MKDIR "%PREFIX%\share\anaconda-mcp"
echo accepted > "%ACCEPTANCE_FLAG%"
echo [OK] EULA accepted. Anaconda MCP installation complete.
echo.
EXIT /B 0