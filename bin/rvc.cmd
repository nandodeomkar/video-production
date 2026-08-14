@echo off
setlocal
set "PROJ_ROOT=%~dp0.."
"%PROJ_ROOT%\vendor\rvc\bin\rvc.cmd" %*
