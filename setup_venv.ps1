$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"

Set-Location $ProjectRoot

if (-not (Test-Path $RequirementsFile)) {
    Write-Error "requirements.txt was not found at: $RequirementsFile"
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment in .venv..."

    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $VenvPath
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $VenvPath
    }
    else {
        Write-Error "Python was not found. Install Python 3.10+ and try again."
    }
}
else {
    Write-Host "Using existing virtual environment in .venv."
}

Write-Host "Installing requirements..."
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r $RequirementsFile

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run the app with:"
Write-Host ".\run_app.ps1"
