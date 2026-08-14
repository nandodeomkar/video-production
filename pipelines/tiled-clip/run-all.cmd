@echo off
setlocal
rem ===========================================================================
rem  Tiled-clip pipeline - run all 4 stages end to end.
rem
rem  Usage:  run-all.cmd  URL  START  END  CLIPNAME  [TILES_FOLDER]
rem    URL           full video URL
rem    START         section start (HH:MM:SS or seconds)
rem    END           section end   (HH:MM:SS or seconds)
rem    CLIPNAME       short name for this clip
rem    TILES_FOLDER   optional custom tile-image folder
rem
rem  Final output:  Output\<CLIPNAME>_tiled.mp4
rem
rem  Stages 1-2 (download, extract) live in pipelines\_shared\ and are reused
rem  by char-clip and pop-clip. Stages 3-4 are tiled-clip's own. Any stage can
rem  be run individually to inspect output or re-run one step.
rem ===========================================================================

if "%~4"=="" (
  echo Usage: run-all.cmd URL START END CLIPNAME [TILES_FOLDER]
  exit /b 1
)

set "URL=%~1"
set "START=%~2"
set "END=%~3"
set "CLIPNAME=%~4"
set "TILES=%~5"
set "HERE=%~dp0"
set "SHARED=%HERE%..\_shared"

call "%SHARED%\1-download.cmd" "%URL%" "%START%" "%END%" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 1. & exit /b 1 )

call "%SHARED%\2-extract-frames.cmd" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 2. & exit /b 1 )

call "%HERE%3-tile-frames.cmd" "%CLIPNAME%" "%TILES%"
if errorlevel 1 ( echo Pipeline aborted at stage 3. & exit /b 1 )

call "%HERE%4-stitch.cmd" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 4. & exit /b 1 )

echo.
echo ==========================================================
echo  Pipeline complete.
echo  Output:  Output\%CLIPNAME%_tiled.mp4
echo ==========================================================
endlocal
