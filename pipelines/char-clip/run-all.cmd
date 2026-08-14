@echo off
setlocal
rem ===========================================================================
rem  char-clip pipeline - run all 4 stages end to end.
rem
rem  Turns a section of an online video into character art (ASCII / mono /
rem  crosshatch), monochrome.
rem
rem  Usage:  run-all.cmd  URL START END CLIPNAME [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
rem    URL        full video URL (paste the bare youtu.be/<id> form -- a
rem               trailing ?si=... share suffix breaks argument parsing)
rem    START      section start (HH:MM:SS or seconds)
rem    END        section end   (HH:MM:SS or seconds)
rem    CLIPNAME   short name for this clip
rem    STYLE      ascii | mono | hatch        (default ascii)
rem    CELL       grid cell size in px        (default 12)
rem    CHAR       single character for STYLE mono (default +)
rem    FILL       none | tint | image        (default none; tint/image colour
rem               the cell backgrounds -- makes scenes far more recognizable)
rem    NORMALIZE  on | off                   (default off; auto-brightens
rem               dark footage)
rem
rem  Final output:  Output\<CLIPNAME>_char.mp4
rem
rem  Stages 1-2 (download, extract) live in pipelines\_shared\ and are shared
rem  by all three pipelines. Stages 3-4 are char-clip's own. Any stage can
rem  be run individually to inspect output or re-run one step.
rem ===========================================================================

if "%~4"=="" (
  echo Usage: run-all.cmd URL START END CLIPNAME [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
  exit /b 1
)

set "URL=%~1"
set "START=%~2"
set "END=%~3"
set "CLIPNAME=%~4"
set "STYLE=%~5"
set "CELL=%~6"
set "CHAR=%~7"
set "FILL=%~8"
set "NORMALIZE=%~9"
set "HERE=%~dp0"
set "SHARED=%HERE%..\_shared"

rem Stages 1-2 are style-agnostic; all three pipelines share them.
call "%SHARED%\1-download.cmd" "%URL%" "%START%" "%END%" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 1. & exit /b 1 )

call "%SHARED%\2-extract-frames.cmd" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 2. & exit /b 1 )

call "%HERE%3-charize-frames.cmd" "%CLIPNAME%" "%STYLE%" "%CELL%" "%CHAR%" "%FILL%" "%NORMALIZE%"
if errorlevel 1 ( echo Pipeline aborted at stage 3. & exit /b 1 )

call "%HERE%4-stitch.cmd" "%CLIPNAME%"
if errorlevel 1 ( echo Pipeline aborted at stage 4. & exit /b 1 )

echo.
echo ==========================================================
echo  Pipeline complete.
echo  Output:  Output\%CLIPNAME%_char.mp4
echo ==========================================================
endlocal
