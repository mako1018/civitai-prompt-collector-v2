param(
    [string]$VenvDir = '.venv'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Find system python
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue).Path
if (-not $pythonCmd) {
    Write-Error "Python が見つかりません。システムに Python をインストールしてください。"
    exit 1
}

Write-Output "Using system python: $pythonCmd"
$venvPath = Join-Path $root $VenvDir

# Create virtual environment if missing
if (-not (Test-Path $venvPath)) {
    Write-Output "Creating virtual environment at $venvPath"
    & $pythonCmd -m venv $venvPath
} else {
    Write-Output "Virtual environment already exists at $venvPath"
}

$venvPython = Join-Path $venvPath 'Scripts\python.exe'

# Upgrade pip
Write-Output "Upgrading pip in venv"
& $venvPython -m pip install --upgrade pip

# Install requirements
if (Test-Path "requirements.txt") {
    Write-Output "Installing requirements into venv (this may take a few minutes)"
    & $venvPython -m pip install -r requirements.txt
} else {
    Write-Output "requirements.txt が見つかりません。手動でパッケージをインストールしてください。"
}

Write-Output "Setup complete. Use the venv python at: $venvPython"
Write-Output "To run Streamlit: & $venvPython -m streamlit run ui/streamlit_app.py --server.port 8503 --server.headless true"
