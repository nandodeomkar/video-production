@echo off
setlocal
rem ===========================================================================
rem  pop-clip: stylize a single image into pop-art / comic-book style.
rem
rem  Standalone entry point -- no pipeline stages, just one image in, one out.
rem  For video, use run-all.cmd instead.
rem
rem  Usage:  stylize-image.cmd INPUT OUTPUT [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
rem    INPUT          source image (png/jpg/...)
rem    OUTPUT         destination image path
rem    COLORS         palette size, k-means clusters   (default 8)
rem    SHADOW_CUTOFF  brightness 0-255 below which halftone dots appear (default 100)
rem    SATURATION     saturation boost factor          (default 1.6)
rem    CELL           halftone dot-grid cell size in px (default 6)
rem    NORMALIZE      on | off                         (default on; auto-brightens.
rem                   pop-art quantization collapses on dark footage, so this
rem                   defaults ON -- pass 'off' only for already-bright images)
rem
rem  Example:  stylize-image.cmd photo.jpg photo_pop.png 8 100 1.6 6 on
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."
set "POPARTDIR=%PROJ_ROOT%\engines\popart"
set "PYEXE=%PROJ_ROOT%\engines\popart\.venv\Scripts\python.exe"

if "%~2"=="" (
  echo Usage: stylize-image.cmd INPUT OUTPUT [COLORS] [SHADOW_CUTOFF] [SATURATION] [CELL] [NORMALIZE]
  exit /b 1
)

rem Resolve INPUT/OUTPUT to absolute paths NOW, while cwd is still the caller's
rem directory. Below we pushd into engines\popart (so popart_render's
rem 'import cv2' resolves), which would otherwise re-root any relative path.
set "INPUT=%~f1"
set "OUTPUT=%~f2"
set "COLORS=%~3"
set "SHADOW=%~4"
set "SATURATION=%~5"
set "CELL=%~6"
set "NORMALIZE=%~7"
if "%COLORS%"=="" set "COLORS=8"
if "%SHADOW%"=="" set "SHADOW=100"
if "%SATURATION%"=="" set "SATURATION=1.6"
if "%CELL%"=="" set "CELL=6"
if "%NORMALIZE%"=="" set "NORMALIZE=on"

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

echo Stylizing %INPUT% -^> %OUTPUT%  ^(colors %COLORS%, cell %CELL%^)
pushd "%POPARTDIR%"
"%PYEXE%" popart_render.py "%INPUT%" "%OUTPUT%" --colors %COLORS% --shadow-cutoff %SHADOW% --saturation %SATURATION% --cell %CELL% %NORMFLAG%
set "RC=%errorlevel%"
popd

if not "%RC%"=="0" (
  echo Stylize failed.
  exit /b 1
)

echo Done: %OUTPUT%
endlocal
