param (
    [string]$ZipPath = "",
    [string]$InstallDir = ".\llama.cpp"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot

function Resolve-ProjectPath {
    param (
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return Join-Path $ProjectRoot $Path
}

if ([string]::IsNullOrWhiteSpace($ZipPath)) {
    $ZipPath = Join-Path (Split-Path $ProjectRoot -Parent) "llama-b8838-bin-win-cuda-13.1-x64.zip"
}

$ZipFullPath = Resolve-ProjectPath $ZipPath
$InstallFullPath = Resolve-ProjectPath $InstallDir

if (-not (Test-Path $ZipFullPath)) {
    Write-Error "llama.cpp zip was not found at: $ZipFullPath"
}

Write-Host "Extracting llama.cpp from: $ZipFullPath"
Write-Host "Install folder: $InstallFullPath"

New-Item -ItemType Directory -Force -Path $InstallFullPath | Out-Null
Expand-Archive -Path $ZipFullPath -DestinationPath $InstallFullPath -Force

$ServerPath = Join-Path $InstallFullPath "llama-server.exe"
if (-not (Test-Path $ServerPath)) {
    Write-Error "llama-server.exe was not found after extraction."
}

Write-Host "llama.cpp was installed. Checking executable..."
& $ServerPath --version
