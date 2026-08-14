# =============================================================================
#  Shared parallel frame renderer for all stylization pipelines.
#
#  Renders every PNG in -FrameDir through a per-frame engine command into
#  -OutDir, running up to -Concurrency frames at once via throttled background
#  jobs. Used by tiled-clip / char-clip / pop-clip Stage 3 scripts.
#
#  Windows PowerShell 5.1 compatible (no ForEach-Object -Parallel).
#
#  Each caller supplies:
#    -PythonExe     full path to the engine's venv python.exe
#    -EngineDir     cwd for the worker (e.g. engines\charart) -- the engine
#                   script and its 'import cv2' must resolve from here
#    -EngineScript  path to the engine .py file (e.g. char_render.py)
#    -EngineArgs    string array of args to pass to the engine, with the
#                   placeholders '{IN}' and '{OUT}' marking where the current
#                   frame's input and output PNG paths should be substituted
#    -FrameDir      folder of input frames (f_*.png)
#    -OutDir        folder to write stylized frames into
#    -Concurrency   max frames in flight at once     (default 8)
#
#  Example caller (char-clip):
#    -EngineArgs @('{IN}', '{OUT}', '--style', 'ascii', '--cell', '12',
#                  '--char', '+', '--fill', 'image', '--normalize')
#
#  Example caller (tiled-clip):
#    -EngineArgs @('{IN}', $picklePath, '{OUT}', $poolSize)
# =============================================================================
param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$EngineDir,
    [Parameter(Mandatory = $true)][string]$EngineScript,
    [Parameter(Mandatory = $true)][string[]]$EngineArgs,
    [Parameter(Mandatory = $true)][string]$FrameDir,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$Concurrency = 8
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir | Out-Null }

$frames = Get-ChildItem -Path $FrameDir -Filter 'f_*.png' | Sort-Object Name
if ($frames.Count -eq 0) {
    Write-Error "No frames found in $FrameDir"
    exit 1
}

Write-Host "Rendering $($frames.Count) frames, $Concurrency at a time via $EngineScript..."

# One job = render one frame. The engine script must run with cwd = EngineDir
# so its 'import cv2' / 'import tiler' resolve against the venv's site-packages
# and any sibling modules. Success is judged by exit code AND the output file
# existing. tqdm-style progress bars on stderr would surface as terminating
# RemoteExceptions inside a job, so ErrorActionPreference is relaxed and stderr
# is merged into stdout.
$worker = {
    param($py, $dir, $script, $perFrameArgs, $expectedOut)
    $ErrorActionPreference = 'Continue'
    Set-Location $dir
    # Why ProcessStartInfo instead of & $py $script @argv:
    # Start-Job deserializes string arrays into ArrayList. PowerShell 5.1's
    # native-command splatter then drops quoting around args that contain
    # spaces -- the receiving exe sees "C:\My Project\file.png" split into two
    # tokens at the space, and argparse reports "missing argument". Using
    # ProcessStartInfo with ArgumentList (and Windows' own CommandLineToArgv
    # round-trip via the .NET BCL) preserves per-arg boundaries reliably.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $py
    $psi.WorkingDirectory = $dir
    $psi.UseShellExecute = $false
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardOutput = $true
    $psi.Arguments = ''  # leave empty; use ArgumentList instead
    [void]$psi.ArgumentList.Add($script)
    foreach ($a in $perFrameArgs) { [void]$psi.ArgumentList.Add([string]$a) }
    $proc = [System.Diagnostics.Process]::Start($psi)
    $stderr = $proc.StandardError.ReadToEnd()
    $stdout = $proc.StandardOutput.ReadToEnd()
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0 -or -not (Test-Path $expectedOut)) {
        throw "engine script failed for '$expectedOut' (exit $($proc.ExitCode)): $stderr$stdout"
    }
}

$jobs = @()
$done = 0
$failed = 0
$total = $frames.Count

foreach ($frame in $frames) {
    # Throttle: wait until a job slot frees up.
    while (@($jobs | Where-Object { $_.State -eq 'Running' }).Count -ge $Concurrency) {
        Wait-Job -Job $jobs -Any | Out-Null
        foreach ($j in @($jobs | Where-Object { $_.State -ne 'Running' })) {
            if ($j.State -eq 'Failed') { $failed++; Write-Warning ($j.ChildJobs[0].JobStateInfo.Reason.Message) }
            try { Receive-Job -Job $j -ErrorAction SilentlyContinue | Out-Null } catch { $failed++; Write-Warning $_.Exception.Message }
            Remove-Job -Job $j
            $done++
        }
        $jobs = @($jobs | Where-Object { $_.State -eq 'Running' })
        Write-Host ("  progress: {0}/{1}" -f $done, $total)
    }

    # Substitute the {IN} and {OUT} placeholders in the engine arg template.
    $outPng = Join-Path $OutDir $frame.Name
    $perFrameArgs = $EngineArgs | ForEach-Object {
        switch ($_) {
            '{IN}'  { $frame.FullName }
            '{OUT}' { $outPng }
            default { $_ }
        }
    }

    $jobs += Start-Job -ScriptBlock $worker -ArgumentList `
        $PythonExe, $EngineDir, $EngineScript, $perFrameArgs, $outPng
}

# Drain remaining jobs.
while ($jobs.Count -gt 0) {
    Wait-Job -Job $jobs -Any | Out-Null
    foreach ($j in @($jobs | Where-Object { $_.State -ne 'Running' })) {
        if ($j.State -eq 'Failed') { $failed++; Write-Warning ($j.ChildJobs[0].JobStateInfo.Reason.Message) }
        try { Receive-Job -Job $j -ErrorAction SilentlyContinue | Out-Null } catch { $failed++; Write-Warning $_.Exception.Message }
        Remove-Job -Job $j
        $done++
    }
    $jobs = @($jobs | Where-Object { $_.State -eq 'Running' })
    Write-Host ("  progress: {0}/{1}" -f $done, $total)
}

if ($failed -gt 0) {
    Write-Error "$failed of $total frames failed to render."
    exit 1
}

Write-Host "All $total frames rendered into $OutDir"
exit 0
