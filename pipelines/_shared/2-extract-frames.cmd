@echo off
setlocal
rem ===========================================================================
rem  Stage 2 of the tiled-clip pipeline: split source.mp4 into a PNG frame
rem  sequence (30fps, 1920x1080) and extract the audio track.
rem
rem  Usage:  2-extract-frames.cmd  CLIPNAME
rem
rem  Reads:   Work\<CLIPNAME>\source.mp4
rem  Output:  Work\<CLIPNAME>\frames\f_000001.png ...   (30fps, 1920x1080)
rem           Work\<CLIPNAME>\audio.m4a                 (original audio, copied)
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."

if "%~1"=="" (
  echo Usage: 2-extract-frames.cmd CLIPNAME
  exit /b 1
)

set "CLIPNAME=%~1"
set "WORKDIR=%PROJ_ROOT%\Work\%CLIPNAME%"
set "SOURCE=%WORKDIR%\source.mp4"
set "FRAMEDIR=%WORKDIR%\frames"

if not exist "%SOURCE%" (
  echo Source not found: %SOURCE%
  echo Run 1-download.cmd first.
  exit /b 1
)

if not exist "%FRAMEDIR%" mkdir "%FRAMEDIR%"

echo [2/4] Extracting 30fps PNG frames to %FRAMEDIR%

rem Store the ffmpeg %06d sequence pattern. 'call' runs its line through
rem percent-expansion an EXTRA time, and each pass halves the percents, so
rem the literal must be %%%%06d: set -> %%06d, then call -> %06d. Writing
rem fewer percents lets %%0 collapse into %0 (the script path).
set "FRAMEPAT=%FRAMEDIR%\f_%%%%06d.png"

rem -nostdin: stop ffmpeg reading the rest of this batch file as keyboard
rem input, which otherwise swallows the commands below it.
rem Single logical line: when reached via run-all.cmd the 'call' re-parses this
rem line, and caret-continued (^) multi-line commands lose trailing args on that
rem extra pass. Keep the whole ffmpeg invocation on one line.
call "%PROJ_ROOT%\bin\ffmpeg.cmd" -nostdin -y -i "%SOURCE%" -vf "fps=30,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black" "%FRAMEPAT%"

if errorlevel 1 (
  echo Frame extraction failed.
  exit /b 1
)

echo [2/4] Extracting audio track to %WORKDIR%\audio.m4a
call "%PROJ_ROOT%\bin\ffmpeg.cmd" -nostdin -y -i "%SOURCE%" -vn -acodec copy "%WORKDIR%\audio.m4a"
if errorlevel 1 (
  echo  No audio track copied ^(clip may be silent^); continuing without audio.
)

echo Done: frames in %FRAMEDIR%
endlocal
