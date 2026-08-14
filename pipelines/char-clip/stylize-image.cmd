@echo off
setlocal
rem ===========================================================================
rem  char-clip: stylize a single image into character art.
rem
rem  Standalone entry point -- no pipeline stages, just one image in, one out.
rem  For video, use run-all.cmd instead.
rem
rem  Usage:  stylize-image.cmd INPUT OUTPUT [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
rem    INPUT      source image (png/jpg/...)
rem    OUTPUT     destination image path
rem    STYLE      ascii | mono | hatch        (default ascii)
rem    CELL       grid cell size in px        (default 12; bigger = coarser)
rem    CHAR       single character for STYLE mono (default +)
rem    FILL       none | tint | image        (default none; tint/image colour
rem               the cell backgrounds -- makes scenes far more recognizable)
rem    NORMALIZE  on | off                   (default off; auto-brightens)
rem
rem  Example:  stylize-image.cmd photo.jpg photo_art.png ascii 10 + image on
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."
set "CHARARTDIR=%PROJ_ROOT%\engines\charart"
set "PYEXE=%PROJ_ROOT%\engines\charart\.venv\Scripts\python.exe"

if "%~2"=="" (
  echo Usage: stylize-image.cmd INPUT OUTPUT [STYLE] [CELL] [CHAR] [FILL] [NORMALIZE]
  exit /b 1
)

rem Resolve INPUT/OUTPUT to absolute paths NOW, while cwd is still the caller's
rem directory. Stage 3 below does pushd into engines\charart (so char_render's
rem 'import cv2' resolves), which would otherwise re-root any relative path.
set "INPUT=%~f1"
set "OUTPUT=%~f2"
set "STYLE=%~3"
set "CELL=%~4"
set "CHAR=%~5"
set "FILL=%~6"
set "NORMALIZE=%~7"
if "%STYLE%"=="" set "STYLE=ascii"
if "%CELL%"==""  set "CELL=12"
if "%CHAR%"==""  set "CHAR=+"
if "%FILL%"==""  set "FILL=none"
if "%NORMALIZE%"=="" set "NORMALIZE=off"

rem --normalize is a presence-only flag: include it only when wanted.
set "NORMFLAG="
if /i "%NORMALIZE%"=="on" set "NORMFLAG=--normalize"

if not exist "%INPUT%" (
  echo Input image not found: %INPUT%
  exit /b 1
)

rem Ensure the output's parent folder exists (cv2.imwrite won't create it).
for %%D in ("%OUTPUT%") do if not exist "%%~dpD" mkdir "%%~dpD"
if not exist "%PYEXE%" (
  echo Python venv not found: %PYEXE%
  exit /b 1
)

echo Stylizing %INPUT% -^> %OUTPUT%  ^(style %STYLE%, cell %CELL%, fill %FILL%^)
pushd "%CHARARTDIR%"
"%PYEXE%" char_render.py "%INPUT%" "%OUTPUT%" --style %STYLE% --cell %CELL% --char "%CHAR%" --fill %FILL% %NORMFLAG%
set "RC=%errorlevel%"
popd

if not "%RC%"=="0" (
  echo Stylize failed.
  exit /b 1
)

echo Done: %OUTPUT%
endlocal
