@echo off
setlocal
set "PROJ_ROOT=%~dp0.."
"%PROJ_ROOT%\vendor\ffmpeg\node_modules\ffmpeg-ffprobe-static\ffmpeg.exe" %*
