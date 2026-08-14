@echo off
setlocal
set "HERE=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%HERE%diagnostics.ps1" %*
endlocal
