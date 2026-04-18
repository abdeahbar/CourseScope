$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AppFile = Join-Path $ProjectRoot "app.py"

Set-Location $ProjectRoot

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found. Run .\setup_venv.ps1 first."
}

if (-not (Test-Path $AppFile)) {
    Write-Error "app.py was not found at: $AppFile"
}

Write-Host "Starting CourseScope..."
& $VenvPython -m streamlit run $AppFile
