# Run Streamlit and capture stdout/stderr to a log file in foreground
param(
    [int]$Port = 8503
)

"""# Note: original file used project-root log paths. Updated to use centralized logs directory.
# Using logs\streamlit_ui_capture.log, logs\streamlit_stdout.log, logs\streamlit_stderr.log
"""
$log = Join-Path -Path $PSScriptRoot -ChildPath "..\logs\streamlit_ui_capture.log"
Write-Output "Starting streamlit on port $Port, logging to $log"

# Run Streamlit in the foreground and redirect both stdout/stderr to the same log file.
# Use the project's venv python if available to ensure correct environment.
$venvPython = Join-Path -Path $PSScriptRoot -ChildPath "..\.venv\Scripts\python.exe"
$outLog = Join-Path -Path $PSScriptRoot -ChildPath "..\logs\streamlit_stdout.log"
$errLog = Join-Path -Path $PSScriptRoot -ChildPath "..\logs\streamlit_stderr.log"

if (Test-Path $venvPython) {
    Write-Output "Starting Streamlit (venv python) on port $Port"
    Start-Process -FilePath $venvPython -ArgumentList '-u','-m','streamlit','run','ui/streamlit_app_collect.py','--server.port',$Port,'--server.headless','true' -RedirectStandardOutput $outLog -RedirectStandardError $errLog -NoNewWindow -PassThru | Out-Null
} else {
    Write-Output "Starting Streamlit (system) on port $Port"
    Start-Process -FilePath 'streamlit' -ArgumentList 'run','ui/streamlit_app_collect.py','--server.port',$Port,'--server.headless','true' -RedirectStandardOutput $outLog -RedirectStandardError $errLog -NoNewWindow -PassThru | Out-Null
}

Write-Output "Streamlit started in background. Stdout -> $outLog, Stderr -> $errLog"
