@echo off
setlocal
set "PROJ_ROOT=%~dp0.."

rem Invoke yt-dlp.exe DIRECTLY, not via vendor\yt-dlp\bin\yt-dlp.cmd.
rem That vendored file is itself a "...exe %*" wrapper, so routing through it
rem meant the arguments were re-expanded by %* TWICE (here, then there). Each
rem batch-to-batch %* hop re-parses the line, and a YouTube URL (with '?',
rem and quotes) does not survive two such re-parses -- yt-dlp ends up with no
rem URL. Calling the .exe directly is a single expansion into a native
rem program, which forwards arguments cleanly.
"%PROJ_ROOT%\vendor\yt-dlp\yt-dlp.exe" %*
