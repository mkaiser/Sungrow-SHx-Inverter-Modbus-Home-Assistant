@echo off
rem Run the Sungrow survey on Windows: double-click this file, or run
rem   survey.cmd [the survey's own arguments]
rem The work is in survey.ps1 beside it; this only starts PowerShell, which
rem will not run a .ps1 on a double-click.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0survey.ps1" %*
set "code=%ERRORLEVEL%"
rem Started from Explorer, the window closes the moment this ends, and the
rem summary with it. Explorer starts cmd with /c and this file's name; a
rem command prompt does not, and there the pause would only be in the way.
echo %CMDCMDLINE% | findstr /i /c:"%~nx0" >nul && pause
exit /b %code%
