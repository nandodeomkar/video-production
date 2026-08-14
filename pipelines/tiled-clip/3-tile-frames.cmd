@echo off
setlocal enabledelayedexpansion
rem ===========================================================================
rem  Stage 3 of the tiled-clip pipeline: tile every frame into a mosaic.
rem
rem  Generates a solid-square tile set once (reused across clips), builds a
rem  shared tiles.pickle, then renders all frames in parallel.
rem
rem  Usage:  3-tile-frames.cmd  CLIPNAME  [TILES_FOLDER]
rem    CLIPNAME      the clip's work-folder name
rem    TILES_FOLDER  optional: a folder of tile images to use instead of the
rem                  auto-generated squares (lets you swap in custom tiles)
rem
rem  Reads:   Work\<CLIPNAME>\frames\f_*.png
rem  Output:  Work\<CLIPNAME>\tiled\f_*.png
rem
rem  Tuning (edit below): SQUARE_SIZE = tile pixel size; bigger = chunkier
rem  mosaic + faster. CONCURRENCY / POOLSIZE control parallelism (16-core box).
rem ===========================================================================

set "PROJ_ROOT=%~dp0..\.."
set "TILERDIR=%PROJ_ROOT%\engines\tiler"
set "PYEXE=%TILERDIR%\.venv\Scripts\python.exe"
set "MAGICK=%PROJ_ROOT%\vendor\imagemagick\dist\magick.exe"

set "SQUARE_SIZE=48"
set "CONCURRENCY=8"
set "POOLSIZE=2"

if "%~1"=="" (
  echo Usage: 3-tile-frames.cmd CLIPNAME [TILES_FOLDER]
  exit /b 1
)

set "CLIPNAME=%~1"
set "WORKDIR=%PROJ_ROOT%\Work\%CLIPNAME%"
set "FRAMEDIR=%WORKDIR%\frames"
set "TILEDDIR=%WORKDIR%\tiled"

if not exist "%FRAMEDIR%" (
  echo Frames not found: %FRAMEDIR%
  echo Run 2-extract-frames.cmd first.
  exit /b 1
)

rem --- Resolve the tile set --------------------------------------------------
if not "%~2"=="" (
  set "TILESET=%~2"
  echo [3/4] Using custom tile set: !TILESET!
) else (
  set "SQUAREDIR=%TILERDIR%\tiles\squares"
  set "TILESET=!SQUAREDIR!\gen_square"
  if not exist "!TILESET!" (
    echo [3/4] Generating solid-square tile set ^(%SQUARE_SIZE%px^)...
    if not exist "!SQUAREDIR!" mkdir "!SQUAREDIR!"
    rem -type TrueColor + PNG24: forces a 3-channel RGB PNG; a flat colour
    rem otherwise saves as 1-channel grayscale, which gen_tiles.py rejects.
    "%MAGICK%" -size %SQUARE_SIZE%x%SQUARE_SIZE% "xc:rgb(240,240,240)" -type TrueColor "PNG24:!SQUAREDIR!\square.png"
    if errorlevel 1 ( echo Failed to create base square. & exit /b 1 )
    pushd "%TILERDIR%"
    "%PYEXE%" gen_tiles.py "!SQUAREDIR!\square.png"
    set "GENRC=!errorlevel!"
    popd
    if not "!GENRC!"=="0" ( echo gen_tiles.py failed. & exit /b 1 )
  ) else (
    echo [3/4] Reusing existing square tile set.
  )
)

if not exist "!TILESET!" (
  echo Tile set folder not found: !TILESET!
  exit /b 1
)

rem --- Build the shared tiles.pickle once ------------------------------------
set "PICKLE=%WORKDIR%\tiles.pickle"
echo [3/4] Building tile cache...
pushd "%TILERDIR%"
"%PYEXE%" build_tiles.py "!TILESET!" "%PICKLE%"
set "PICKRC=!errorlevel!"
popd
if not "!PICKRC!"=="0" ( echo build_tiles.py failed. & exit /b 1 )

rem --- Render all frames in parallel -----------------------------------------
echo [3/4] Tiling frames in parallel...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\_shared\render-frames.ps1" ^
  -PythonExe "%PYEXE%" ^
  -EngineDir "%TILERDIR%" ^
  -EngineScript "tile_frame.py" ^
  -EngineArgs '{IN}','%PICKLE%','{OUT}','%POOLSIZE%' ^
  -FrameDir "%FRAMEDIR%" ^
  -OutDir "%TILEDDIR%" ^
  -Concurrency %CONCURRENCY%

if errorlevel 1 (
  echo Tiling failed.
  exit /b 1
)

echo Done: tiled frames in %TILEDDIR%
endlocal
