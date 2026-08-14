@echo off
setlocal
rem ===========================================================================
rem  Stage 4 of the tiled-clip pipeline: stitch tiled frames back into a video.
rem
rem  Re-encodes the tiled PNG sequence at 30fps and reattaches the original
rem  audio. yuv420p flattens any RGBA transparency over black and ensures the
rem  result imports cleanly into any video editor.
rem
rem  Usage:  4-stitch.cmd  CLIPNAME
rem
rem  Reads:   Work\<CLIPNAME>\tiled\f_*.png
rem           Work\<CLIPNAME>\audio.m4a   (optional; omitted if absent)
rem  Output:  Output\<CLIPNAME>_tiled.mp4
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."

if "%~1"=="" (
  echo Usage: 4-stitch.cmd CLIPNAME
  exit /b 1
)

set "CLIPNAME=%~1"
set "WORKDIR=%PROJ_ROOT%\Work\%CLIPNAME%"
set "TILEDDIR=%WORKDIR%\tiled"
set "AUDIO=%WORKDIR%\audio.m4a"
set "OUTDIR=%PROJ_ROOT%\Output"
set "OUTFILE=%OUTDIR%\%CLIPNAME%_tiled.mp4"

if not exist "%TILEDDIR%\f_000001.png" (
  echo Tiled frames not found: %TILEDDIR%
  echo Run 3-tile-frames.cmd first.
  exit /b 1
)

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

rem Store the %06d input pattern. 'call' re-expands its line once more, and
rem each pass halves the percents, so the literal must be %%%%06d: set ->
rem %%06d, then call -> %06d. See the same fix in 2-extract-frames.cmd.
set "FRAMEPAT=%TILEDDIR%\f_%%%%06d.png"

rem -nostdin: stop ffmpeg consuming the rest of this batch file as input.
rem Each ffmpeg call is kept on ONE logical line: when reached via run-all.cmd
rem the 'call' re-parses the line, and caret-continued (^) multi-line commands
rem lose trailing args on that extra pass.
if exist "%AUDIO%" (
  echo [4/4] Stitching tiled frames + audio into %OUTFILE%
  call "%PROJ_ROOT%\bin\ffmpeg.cmd" -nostdin -y -framerate 30 -i "%FRAMEPAT%" -i "%AUDIO%" -vf "format=yuv420p" -c:v libx264 -crf 18 -preset slow -c:a aac -b:a 192k -shortest "%OUTFILE%"
) else (
  echo [4/4] Stitching tiled frames into %OUTFILE% ^(no audio^)
  call "%PROJ_ROOT%\bin\ffmpeg.cmd" -nostdin -y -framerate 30 -i "%FRAMEPAT%" -vf "format=yuv420p" -c:v libx264 -crf 18 -preset slow "%OUTFILE%"
)

if errorlevel 1 (
  echo Stitching failed.
  exit /b 1
)

echo Done: %OUTFILE%
endlocal
