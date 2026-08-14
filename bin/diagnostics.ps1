# diagnostics.ps1 - Verify the Video Production project environment and tool wrappers.
# Part of the Project Organization.

$Host.UI.RawUI.WindowTitle = "Video Production Toolkit - Environment Diagnostics"

# Colors and formatting helpers
function Write-Header ($text) {
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan -Bold
    Write-Host "======================================================================" -ForegroundColor Cyan
}

function Write-Section ($text) {
    Write-Host ""
    Write-Host "--- $text ---" -ForegroundColor Yellow -Bold
}

function Write-Success ($name, $details = "") {
    Write-Host "  [+] SUCCESS: " -NoNewline -ForegroundColor Green
    Write-Host "$name" -NoNewline -ForegroundColor White
    if ($details) {
        Write-Host " ($details)" -ForegroundColor Gray
    } else {
        Write-Host ""
    }
}

function Write-Warning-Check ($name, $details = "") {
    Write-Host "  [!] WARNING: " -NoNewline -ForegroundColor Yellow
    Write-Host "$name" -NoNewline -ForegroundColor White
    if ($details) {
        Write-Host " ($details)" -ForegroundColor Gray
    } else {
        Write-Host ""
    }
}

function Write-Failure ($name, $errorMsg) {
    Write-Host "  [-] FAILURE: " -NoNewline -ForegroundColor Red
    Write-Host "$name" -ForegroundColor White
    Write-Host "               Error: $errorMsg" -ForegroundColor Red
}

# Resolve project root path
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjRoot = Resolve-Path (Join-Path $ScriptDir "..")
$EnginesDir = Join-Path $ProjRoot "engines"
$VendorDir = Join-Path $ProjRoot "vendor"
$AppsDir = Join-Path $ProjRoot "apps"
$BinDir = Join-Path $ProjRoot "bin"

Write-Header "Video Production Environment Diagnostics"
Write-Host "Project Root: $ProjRoot" -ForegroundColor Gray

# ----------------------------------------------------------------------
# 1. Directory Structure Checks
# ----------------------------------------------------------------------
Write-Section "Directory Structure Integrity"

$RequiredDirs = @(
    "bin",
    "apps",
    "pipelines",
    "engines",
    "vendor",
    "Work",
    "Output",
    "docs",
    "docs\workflows"
)

foreach ($dir in $RequiredDirs) {
    $path = Join-Path $ProjRoot $dir
    if (Test-Path $path -PathType Container) {
        Write-Success "$dir/" "Directory exists"
    } else {
        Write-Failure "$dir/" "Folder is missing! Please recreate the directory '$dir/' in the root."
    }
}

# ----------------------------------------------------------------------
# 2. Command Line Wrappers & System Binaries
# ----------------------------------------------------------------------
Write-Section "Command Line Wrappers (bin/)"

$Wrappers = @{
    "ffmpeg.cmd" = "-version"
    "ffprobe.cmd" = "-version"
    "yt-dlp.cmd" = "--version"
    "magick.cmd" = "-version"
}

foreach ($item in $Wrappers.GetEnumerator()) {
    $wrapperName = $item.Key
    $arg = $item.Value
    $wrapperPath = Join-Path $BinDir $wrapperName
    
    if (Test-Path $wrapperPath) {
        try {
            # Execute wrapper to verify it runs and calls the underlying binary
            $procInfo = New-Object System.Diagnostics.ProcessStartInfo
            $procInfo.FileName = $wrapperPath
            $procInfo.Arguments = $arg
            $procInfo.RedirectStandardOutput = $true
            $procInfo.RedirectStandardError = $true
            $procInfo.UseShellExecute = $false
            $procInfo.CreateNoWindow = $true
            
            $proc = [System.Diagnostics.Process]::Start($procInfo)
            $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
            $stderrTask = $proc.StandardError.ReadToEndAsync()
            
            # Wait up to 5 seconds for completion
            if ($proc.WaitForExit(5000)) {
                $stdout = $stdoutTask.Result
                $stderr = $stderrTask.Result
                
                if ($proc.ExitCode -eq 0) {
                    # Extract the first line of output for a brief version detail
                    $firstLine = @($stdout -split "`r?`n" | Where-Object { $_.Trim() })[0]
                    if ($firstLine -match "ffmpeg version") {
                        $firstLine = $firstLine -split " Copyright" | Select-Object -First 1
                    }
                    if ($firstLine -match "ffprobe version") {
                        $firstLine = $firstLine -split " Copyright" | Select-Object -First 1
                    }
                    Write-Success $wrapperName $firstLine.Trim()
                } else {
                    # Some commands might fail with status queries but still exist
                    $errText = ($stderr + " " + $stdout).Trim()
                    if ($errText.Length -gt 80) { $errText = $errText.Substring(0, 80) + "..." }
                    Write-Warning-Check $wrapperName "Exited with code $($proc.ExitCode). Output: $errText"
                }
            } else {
                $proc.Kill()
                Write-Failure $wrapperName "Command timed out after 5 seconds"
            }
        } catch {
            Write-Failure $wrapperName "Execution failed! $($_.Exception.Message)"
        }
    } else {
        Write-Failure $wrapperName "File is missing! Make sure '$wrapperName' is located in 'bin/'."
    }
}

# Verify GUI app launchers
$appLaunchers = @{
    "smart-char-art"      = Join-Path $AppsDir "smart-char-art\launch.cmd"
    "smart-logo-remover"  = Join-Path $AppsDir "smart-logo-remover\launch.cmd"
}
foreach ($app in $appLaunchers.GetEnumerator()) {
    if (Test-Path $app.Value) {
        Write-Success "apps\$($app.Key)\launch.cmd" "Launcher exists"
    } else {
        Write-Failure "apps\$($app.Key)\launch.cmd" "Launcher file is missing!"
    }
}

# ----------------------------------------------------------------------
# 3. Python Environments & Libraries
# ----------------------------------------------------------------------
Write-Section "Python Virtual Environments & Custom Engines"

# Generic venv import check, used for all four engines.
function Test-Venv ($Label, $VenvPython, $ImportLine, $MissingHint) {
    if (Test-Path $VenvPython) {
        try {
            $importCheck = & $VenvPython -c $ImportLine 2>&1
            if ($importCheck -eq "OK") {
                Write-Success $Label "Imports OK ($ImportLine)"
            } else {
                Write-Failure $Label "Failed import! Output: $importCheck"
            }
        } catch {
            Write-Failure $Label "Execution of python failed! $($_.Exception.Message)"
        }
    } else {
        Write-Failure $Label $MissingHint
    }
}

# A. Tiler venv (powers the tiled-clip pipeline only)
$TilerVenv   = Join-Path $EnginesDir "tiler\.venv\Scripts\python.exe"
Test-Venv "engines\tiler\.venv"        $TilerVenv "import numpy, cv2, tqdm; print('OK')" "Venv missing at 'engines/tiler/.venv/'. From engines/tiler: 'python -m venv .venv' then '.venv\Scripts\pip install -r requirements.txt'."

# B. CharArt venv (powers the char-clip pipeline and the Smart CharArt GUI)
$CharArtVenv = Join-Path $EnginesDir "charart\.venv\Scripts\python.exe"
Test-Venv "engines\charart\.venv"      $CharArtVenv "import numpy, cv2; print('OK')" "Venv missing at 'engines/charart/.venv/'. From engines/charart: 'python -m venv .venv' then '.venv\Scripts\pip install -r requirements.txt'."

# C. PopArt venv (powers the pop-clip pipeline)
$PopArtVenv  = Join-Path $EnginesDir "popart\.venv\Scripts\python.exe"
Test-Venv "engines\popart\.venv"       $PopArtVenv "import numpy, cv2; print('OK')" "Venv missing at 'engines/popart/.venv/'. From engines/popart: 'python -m venv .venv' then '.venv\Scripts\pip install -r requirements.txt'."

# D. Logo-remover venv (powers remove-logo.cmd and the Smart Logo Remover GUI)
$LogoVenv    = Join-Path $EnginesDir "logo-remover\.venv\Scripts\python.exe"
Test-Venv "engines\logo-remover\.venv" $LogoVenv "import numpy, cv2, tkinter; print('OK')" "Venv missing at 'engines/logo-remover/.venv/'. From engines/logo-remover: 'python -m venv .venv' then '.venv\Scripts\pip install numpy opencv-python'."

# E. PopArt Render Engine Tests (run under PopArt's own venv)
$PopArtTestDir = Join-Path $EnginesDir "popart"
$PopArtTest = Join-Path $PopArtTestDir "test_popart_render.py"
if (Test-Path $PopArtTest) {
    Write-Host ""
    Write-Host "Running PopArt Engine Unit Tests..." -ForegroundColor Cyan
    try {
        Push-Location $PopArtTestDir
        $testResult = & $PopArtVenv -m unittest test_popart_render -v 2>&1
        $passed = $true
        foreach ($line in $testResult) {
            Write-Host "  $line" -ForegroundColor Gray
            if ($line -match "FAILED" -or $line -match "errors=") {
                $passed = $false
            }
        }
        if ($passed) {
            Write-Success "PopArt Engine Tests" "All unit tests passed successfully"
        } else {
            Write-Failure "PopArt Engine Tests" "Some unit tests failed! Inspect the output above."
        }
    } catch {
        Write-Failure "PopArt Engine Tests" "Could not execute PopArt unit tests! $($_.Exception.Message)"
    } finally {
        Pop-Location
    }
} else {
    Write-Warning-Check "PopArt Engine Tests" "test_popart_render.py not found in engines/popart/"
}

# F. CharArt Render Engine Tests (run under CharArt's own venv)
$CharArtTestDir = Join-Path $EnginesDir "charart"
$CharArtTest = Join-Path $CharArtTestDir "test_char_render.py"
if (Test-Path $CharArtTest) {
    Write-Host ""
    Write-Host "Running CharArt Engine Unit Tests..." -ForegroundColor Cyan
    try {
        Push-Location $CharArtTestDir
        $testResult = & $CharArtVenv -m unittest test_char_render -v 2>&1
        $passed = $true
        foreach ($line in $testResult) {
            Write-Host "  $line" -ForegroundColor Gray
            if ($line -match "FAILED" -or $line -match "errors=") {
                $passed = $false
            }
        }
        if ($passed) {
            Write-Success "CharArt Engine Tests" "All unit tests passed successfully"
        } else {
            Write-Failure "CharArt Engine Tests" "Some unit tests failed! Inspect the output above."
        }
    } catch {
        Write-Failure "CharArt Engine Tests" "Could not execute CharArt unit tests! $($_.Exception.Message)"
    } finally {
        Pop-Location
    }
} else {
    Write-Warning-Check "CharArt Engine Tests" "test_char_render.py not found in engines/charart/"
}


Write-Header "Diagnostics Complete"
Write-Host "If any checks failed, please review the instructions in README.md to resolve them." -ForegroundColor Yellow
Write-Host ""
