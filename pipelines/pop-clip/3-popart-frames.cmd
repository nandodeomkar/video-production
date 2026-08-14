@echo off
setlocal enabledelayedexpansion
rem ===========================================================================
rem  Stage 3 of the pop-clip pipeline: stylize every frame into pop-art.
rem
rem  popart_render.py is pure cv2/numpy. Frames are rendered in parallel.
rem
rem  Usage:  3-popart-frames.cmd  CLIPNAME  [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
rem    CLIPNAME       the clip's work-folder name
rem    COLORS         palette size, k-means clusters   (default 8)
rem    SHADOW_CUTOFF  brightness 0-255 below which halftone dots appear (default 100)
rem    SATURATION     saturation boost factor          (default 1.6)
rem    CELL           halftone dot-grid cell size in px (default 6)
rem    NORMALIZE      on | off                         (default on; auto-brightens.
rem                   pop-art quantization collapses on dark footage, so this
rem                   defaults ON -- pass 'off' only for already-bright clips)
rem
rem  Reads:   Work\<CLIPNAME>\frames\f_*.png
rem  Output:  Work\<CLIPNAME>\popart\f_*.png
rem
rem  Tuning: CONCURRENCY = how many frames render at once (default 8, tuned for
rem  a 16-core box -- popart_render is single-process so 1 core per frame).
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."
set "POPARTDIR=%PROJ_ROOT%\engines\popart"
set "PYEXE=%PROJ_ROOT%\engines\popart\.venv\Scripts\python.exe"

set "CONCURRENCY=8"

if "%~1"=="" (
  echo Usage: 3-popart-frames.cmd CLIPNAME [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
  exit /b 1
)

set "CLIPNAME=%~1"
set "COLORS=%~2"
set "SHADOW=%~3"
set "SATURATION=%~4"
set "CELL=%~5"
set "NORMALIZE=%~6"
if "%COLORS%"=="" set "COLORS=8"
if "%SHADOW%"=="" set "SHADOW=100"
if "%SATURATION%"=="" set "SATURATION=1.6"
if "%CELL%"=="" set "CELL=6"
if "%NORMALIZE%"=="" set "NORMALIZE=on"

rem popart_render's --normalize is presence-only: include the literal token in
rem the engine args ONLY when wanted.
set "NORMARG="
if /i "%NORMALIZE%"=="on" set "NORMARG=,'--normalize'"

set "WORKDIR=%PROJ_ROOT%\Work\%CLIPNAME%"
set "FRAMEDIR=%WORKDIR%\frames"
set "OUTDIR=%WORKDIR%\popart"

if not exist "%FRAMEDIR%" (
  echo Frames not found: %FRAMEDIR%
  echo Run 2-extract-frames.cmd first.
  exit /b 1
)
if not exist "%PYEXE%" (
  echo Python venv not found: %PYEXE%
  exit /b 1
)

echo [3/4] Pop-arting frames in parallel ^(colors %COLORS%, cell %CELL%^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\_shared\render-frames.ps1" ^
  -PythonExe "%PYEXE%" ^
  -EngineDir "%POPARTDIR%" ^
  -EngineScript "popart_render.py" ^
  -EngineArgs '{IN}','{OUT}','--colors','%COLORS%','--shadow-cutoff','%SHADOW%','--saturation','%SATURATION%','--cell','%CELL%'%NORMARG% ^
  -FrameDir "%FRAMEDIR%" ^
  -OutDir "%OUTDIR%" ^
  -Concurrency %CONCURRENCY%

if errorlevel 1 (
  echo Pop-arting failed.
  exit /b 1
)

echo Done: pop-arted frames in %OUTDIR%
endlocal
