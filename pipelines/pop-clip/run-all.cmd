@echo off
setlocal
rem ===========================================================================
rem  pop-clip pipeline - run all 4 stages end to end.
rem
rem  Turns a section of an online video into pop-art / comic-book style:
rem  flat saturated colour, halftone dots in shadows, bold black outlines.
rem
rem  Usage:  run-all.cmd  URL START END CLIPNAME [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
rem    URL            full video URL (paste the bare youtu.be/<id> form -- a
rem                   trailing ?si=... share suffix breaks argument parsing)
rem    START          section start (HH:MM:SS or seconds)
rem    END            section end   (HH:MM:SS or seconds)
rem    CLIPNAME       short name for this clip
rem    COLORS         palette size, k-means clusters   (default 8)
rem    SHADOW_CUTOFF  brightness 0-255 below which halftone dots appear (default 100)
rem    SATURATION     saturation boost factor          (default 1.6)
rem    CELL           halftone dot-grid cell size in px (default 6)
rem    NORMALIZE      on | off                         (default on; auto-brightens.
rem                   pop-art quantization collapses on dark footage, so this
rem                   defaults ON -- pass 'off' only for already-bright clips)
rem
rem  Final output:  Output\<CLIPNAME>_popart.mp4
rem
rem  Stages 1-2 (download, extract) live in pipelines\_shared\ and are shared
rem  by all three pipelines. Stages 3-4 are pop-clip's own. Any stage can
rem  be run individually to inspect output or re-run one step.
rem ===========================================================================

if "%~4"=="" (
  echo Usage: run-all.cmd URL START END CLIPNAME [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
  exit /b 1
)

set "URL=%~1"
set "START=%~2"
set "END=%~3"
set "CLIPNAME=%~4"
set "COLORS=%~5"
set "SHADOW=%~6"
set "SATURATION=%~7"
set "CELL=%~8"
set "NORMALIZE=%~9"
set "HERE=%~dp0"
set "SHARED=%HERE%..\_shared"

rem Stages 1-2 are style-agnostic; all three pipelines share them.
call "%SHARED%\1-download.cmd" "%URL%" "%START%" "%END%" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 1. & exit /b 1 )

call "%SHARED%\2-extract-frames.cmd" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 2. & exit /b 1 )

call "%HERE%3-popart-frames.cmd" "%CLIPNAME%" "%COLORS%" "%SHADOW%" "%SATURATION%" "%CELL%" "%NORMALIZE%"
if errorlevel 1 ( echo Pipeline aborted at stage 3. & exit /b 1 )

call "%HERE%4-stitch.cmd" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 4. & exit /b 1 )

echo.
echo ==========================================================
echo  Pipeline complete.
echo  Output:  Output\%CLIPNAME%_popart.mp4
echo ==========================================================
endlocal
