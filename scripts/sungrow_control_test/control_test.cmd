@echo off
rem Run the Sungrow control test on Windows, from a command prompt:
rem   control_test.cmd <host> --dry-run
rem It WRITES TO YOUR INVERTER; --dry-run writes nothing. The work is in
rem control_test.ps1 beside it; this only starts PowerShell, which will not
rem run a .ps1 on a double-click.
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0control_test.ps1" %*
set "code=%ERRORLEVEL%"
rem Started from Explorer, the window closes the moment this ends, and the
rem summary with it. Explorer starts cmd with /c and this file's name; a
rem command prompt does not, and there the pause would only be in the way.
echo %CMDCMDLINE% | findstr /i /c:"%~nx0" >nul && pause
exit /b %code%
