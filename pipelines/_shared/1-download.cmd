@echo off
setlocal
rem ===========================================================================
rem  Stage 1 of the tiled-clip pipeline: download a trimmed YouTube section.
rem
rem  Usage:  1-download.cmd  URL  START  END  CLIPNAME
rem    URL       full video URL
rem    START     section start, as HH:MM:SS or seconds (e.g. 00:01:30 or 90)
rem    END       section end,   as HH:MM:SS or seconds
rem    CLIPNAME  short name for this clip (used as the work-folder name)
rem
rem  Output:  Work\<CLIPNAME>\source.mp4   (trimmed, up to 1080p, h264/mp4)
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."

if "%~4"=="" (
  echo Usage: 1-download.cmd URL START END CLIPNAME
  exit /b 1
)

set "URL=%~1"
set "START=%~2"
set "END=%~3"
set "CLIPNAME=%~4"

rem Strip everything from the first '&' onward. A YouTube URL only needs the
rem video id (...?v=ID or youtu.be/ID); '&'-joined params (&t=, &list=, &pp=,
rem the &-half of an ?si= share link) are disposable. They are also actively
rem harmful: '&' is the cmd command separator, and a URL carrying one gets
rem split apart at every parse layer (cmd /c, nested call) no matter how it is
rem quoted -- yt-dlp then sees a truncated/empty URL. Removing the '&' tail
rem makes the URL intrinsically safe to pass around. for /f with delims=&
rem keeps only the text before the first '&'.
for /f "delims=&" %%U in ("%URL%") do set "URL=%%U"

set "WORKDIR=%PROJ_ROOT%\Work\%CLIPNAME%"
if not exist "%WORKDIR%" mkdir "%WORKDIR%"

echo [1/4] Downloading section %START%-%END% from %URL%

rem yt-dlp call kept on ONE line on purpose. When this script is reached via
rem run-all.cmd, the 'call' re-parses this line; a caret-continued (^) multi-line
rem command does not survive that extra pass cleanly and the trailing "%URL%"
rem argument gets dropped. A single logical line has nothing for the re-parse
rem to mangle.
rem
rem The -o template is the LITERAL "source.mp4", not yt-dlp's "%(ext)s"
rem placeholder: under run-all.cmd's nested 'call' the line is parsed twice,
rem and on the second pass cmd mis-reads the '%(' of '%(ext)s', eats it, and
rem fuses the following "%URL%" argument onto the -o value -- yt-dlp then sees
rem no URL. --merge-output-format mp4 plus the h264 format sort already force
rem an .mp4 output, and the success check below also assumes source.mp4, so a
rem fixed name is both safe to parse and consistent.
call "%PROJ_ROOT%\bin\yt-dlp.cmd" --download-sections "*%START%-%END%" --force-keyframes-at-cuts -S "res:1080,fps,vcodec:h264" --merge-output-format mp4 --no-playlist -o "%WORKDIR%\source.mp4" "%URL%"

if errorlevel 1 (
  echo Download failed.
  exit /b 1
)

if not exist "%WORKDIR%\source.mp4" (
  echo Expected output not found: %WORKDIR%\source.mp4
  echo  ^(yt-dlp may have produced a different container; check %WORKDIR%^)
  exit /b 1
)

echo Done: %WORKDIR%\source.mp4
endlocal
