@echo off
setlocal

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "SCRIPT_PY=%~dp0remove_logo.py"

if "%~1"=="" (
    echo Usage: remove-logo.cmd INPUT_VIDEO [OUTPUT_VIDEO]
    echo.
    echo If OUTPUT_VIDEO is omitted, it will be saved as INPUT_VIDEO_nologo.mp4
    exit /b 1
)

set "INPUT_VIDEO=%~1"
set "OUTPUT_VIDEO=%~2"

:: Extract directory, name, and extension of the input file outside of the IF block
for %%i in ("%INPUT_VIDEO%") do (
    set "FILE_DIR=%%~dpi"
    set "FILE_NAME=%%~ni"
    set "FILE_EXT=%%~xi"
)

if "%OUTPUT_VIDEO%"=="" (
    set "OUTPUT_VIDEO=%FILE_DIR%%FILE_NAME%_nologo%FILE_EXT%"
)

echo Starting Interactive Logo Remover...
echo Input:  %INPUT_VIDEO%
echo Output: %OUTPUT_VIDEO%
echo.

"%PYTHON_EXE%" "%SCRIPT_PY%" "%INPUT_VIDEO%" "%OUTPUT_VIDEO%"

endlocal
