@echo off
setlocal
set "PROJ_ROOT=%~dp0.."
"%PROJ_ROOT%\vendor\imagemagick\bin\magick.cmd" %*
