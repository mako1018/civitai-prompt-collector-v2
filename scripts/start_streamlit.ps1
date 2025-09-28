param(
    [int]$Port = 8504,
    [string]$LogDir = "logs"
)

# Determine project root (one level up from scripts/)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir '..')

# Ensure log directory
$logPath = Join-Path $projectRoot $LogDir
if (-not (Test-Path $logPath)) { New-Item -ItemType Directory -Path $logPath | Out-Null }

Write-Host "[start_streamlit] Project root: $projectRoot"
Write-Host "[start_streamlit] Logs: $logPath"
Write-Host "[start_streamlit] Port: $Port"

# If something is listening on the port, try to stop the owning process
try {
    $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($conn) {
        $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pid in $pids) {
            try {
                Write-Host "[start_streamlit] Stopping process $pid that listens on port $Port"
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Warning ("Failed to stop process {0}: {1}" -f $pid, $_)
            }
        }
    }
} catch {
    Write-Verbose "Get-NetTCPConnection not available or failed: $_"
}

# Build command
$streamlitScript = Join-Path $projectRoot "ui\streamlit_app.py"
$stdoutFile = Join-Path $logPath "streamlit_$Port.log"
$stderrFile = Join-Path $logPath "streamlit_$Port.err"

# Start Streamlit as a detached process and redirect output to log files
Write-Host "[start_streamlit] Starting Streamlit: python -m streamlit run $streamlitScript --server.port $Port --server.headless true"
try {
    $pythonPath = (Get-Command python).Source
    $procArgs = @('-m','streamlit','run', $streamlitScript, '--server.port', $Port, '--server.headless', 'true')
    # Start-Process with RedirectStandardOutput/RedirectStandardError returns a Process object
    $proc = Start-Process -FilePath $pythonPath -ArgumentList $procArgs -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile -PassThru
    Start-Sleep -Seconds 2
    if ($proc) {
        Write-Host "[start_streamlit] Streamlit started (PID: $($proc.Id)). Logs: $stdoutFile, $stderrFile"
    } else {
        Write-Warning "Start-Process returned no process object; attempting fallback"
        throw "NoProc"
    }
} catch {
    Write-Warning ("Failed to start Streamlit via Start-Process: {0}" -f $_)
    Write-Host "Trying fallback: starting via cmd start"
    try {
        Start-Process -FilePath 'cmd' -ArgumentList '/c','start','""','python','-m','streamlit','run', $streamlitScript, '--server.port', $Port, '--server.headless','true' -WindowStyle Hidden
    } catch {
        Write-Error ("Fallback start also failed: {0}" -f $_)
    }
}

# Open browser to localhost
Start-Sleep -Seconds 1
try {
    Start-Process "http://localhost:$Port"
    Write-Host "[start_streamlit] Opened browser at http://localhost:$Port"
} catch {
    Write-Warning "Could not open browser automatically: $_"
}
