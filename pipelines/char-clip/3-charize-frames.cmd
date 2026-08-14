@echo off
setlocal enabledelayedexpansion
rem ===========================================================================
rem  Stage 3 of the char-clip pipeline: stylize every frame into character art.
rem
rem  Unlike the tiled-clip equivalent there is no tile set to generate or cache
rem  -- char_render.py is pure NumPy. Frames are rendered in parallel.
rem
rem  Usage:  3-charize-frames.cmd  CLIPNAME  [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
rem    CLIPNAME   the clip's work-folder name
rem    STYLE      ascii | mono | hatch        (default ascii)
rem    CELL       grid cell size in px        (default 12)
rem    CHAR       single character for STYLE mono (default +)
rem    FILL       none | tint | image        (default none; tint/image make
rem               scenes far more recognizable by colouring cell backgrounds)
rem    NORMALIZE  on | off                   (default off; auto-brightens
rem               dark footage before stylizing)
rem
rem  Reads:   Work\<CLIPNAME>\frames\f_*.png
rem  Output:  Work\<CLIPNAME>\charized\f_*.png
rem
rem  Tuning: CONCURRENCY = how many frames render at once (default 8, tuned for
rem  a 16-core box -- char_render is single-process so 1 core per frame).
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."
set "CHARARTDIR=%PROJ_ROOT%\engines\charart"
set "PYEXE=%PROJ_ROOT%\engines\charart\.venv\Scripts\python.exe"

set "CONCURRENCY=8"

if "%~1"=="" (
  echo Usage: 3-charize-frames.cmd CLIPNAME [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
  exit /b 1
)

set "CLIPNAME=%~1"
set "STYLE=%~2"
set "CELL=%~3"
set "CHAR=%~4"
set "FILL=%~5"
set "NORMALIZE=%~6"
if "%STYLE%"=="" set "STYLE=ascii"
if "%CELL%"==""  set "CELL=12"
if "%CHAR%"==""  set "CHAR=+"
if "%FILL%"==""  set "FILL=none"
if "%NORMALIZE%"=="" set "NORMALIZE=off"

rem char_render's --normalize is presence-only: include the literal token in the
rem engine args ONLY when wanted. The shared render-frames.ps1 forwards all
rem tokens to the engine script as positional/flag args.
set "NORMARG="
if /i "%NORMALIZE%"=="on" set "NORMARG=,'--normalize'"

set "WORKDIR=%PROJ_ROOT%\Work\%CLIPNAME%"
set "FRAMEDIR=%WORKDIR%\frames"
set "OUTDIR=%WORKDIR%\charized"

if not exist "%FRAMEDIR%" (
  echo Frames not found: %FRAMEDIR%
  echo Run 2-extract-frames.cmd first.
  exit /b 1
)
if not exist "%PYEXE%" (
  echo Python venv not found: %PYEXE%
  exit /b 1
)

echo [3/4] Charizing frames in parallel ^(style %STYLE%, cell %CELL%, fill %FILL%^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\_shared\render-frames.ps1" ^
  -PythonExe "%PYEXE%" ^
  -EngineDir "%CHARARTDIR%" ^
  -EngineScript "char_render.py" ^
  -EngineArgs '{IN}','{OUT}','--style','%STYLE%','--cell','%CELL%','--char','%CHAR%','--fill','%FILL%'%NORMARG% ^
  -FrameDir "%FRAMEDIR%" ^
  -OutDir "%OUTDIR%" ^
  -Concurrency %CONCURRENCY%

if errorlevel 1 (
  echo Charizing failed.
  exit /b 1
)

echo Done: charized frames in %OUTDIR%
endlocal
