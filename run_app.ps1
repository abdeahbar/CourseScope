$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AppFile = Join-Path $ProjectRoot "app.py"
$OllamaApiUrl = "http://127.0.0.1:11434/api/tags"
$OllamaWaitSeconds = 90
$OutputPath = Join-Path $ProjectRoot "output"
$OllamaOutLog = Join-Path $OutputPath "ollama-stdout.log"
$OllamaErrLog = Join-Path $OutputPath "ollama-stderr.log"
$BadOllamaEnvVars = @(
    "OLLAMA_LLM_LIBRARY",
    "OLLAMA_NUM_GPU",
    "OLLAMA_VULKAN",
    "CUDA_VISIBLE_DEVICES"
)

Set-Location $ProjectRoot

function Clear-BadOllamaEnvironment {
    foreach ($Name in $BadOllamaEnvVars) {
        Remove-Item "Env:$Name" -ErrorAction SilentlyContinue
    }
}

function Set-CourseScopeOllamaEnvironment {
    Clear-BadOllamaEnvironment

    # Keep local runs responsive even if a large global Ollama context is configured.
    $env:OLLAMA_CONTEXT_LENGTH = "4096"
    $env:OLLAMA_FLASH_ATTENTION = "true"
    $env:OLLAMA_HOST = "127.0.0.1:11434"
}

function Stop-OllamaProcesses {
    $ProcessNames = @(
        "ollama",
        "ollama app",
        "ollama_llama_server"
    )

    foreach ($Name in $ProcessNames) {
        Get-Process -Name $Name -ErrorAction SilentlyContinue | Stop-Process -Force
    }

    Start-Sleep -Seconds 2
}

function Test-OllamaApi {
    try {
        Invoke-RestMethod -Uri $OllamaApiUrl -Method Get -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-OllamaApi {
    param (
        [int]$TimeoutSeconds
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        if (Test-OllamaApi) {
            return $true
        }

        Start-Sleep -Seconds 1
    }

    return $false
}

if (-not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found. Run .\setup_venv.ps1 first."
}

if (-not (Test-Path $AppFile)) {
    Write-Error "app.py was not found at: $AppFile"
}

Set-CourseScopeOllamaEnvironment
$OllamaCommand = Get-Command ollama -ErrorAction SilentlyContinue

if (-not $OllamaCommand) {
    Write-Warning "Ollama was not found in PATH. Install Ollama or start it manually."
}
else {
    Write-Host "Restarting Ollama with CourseScope settings..."
    Stop-OllamaProcesses
    New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null

    $OllamaProcess = Start-Process `
        -FilePath $OllamaCommand.Source `
        -ArgumentList "serve" `
        -WindowStyle Hidden `
        -RedirectStandardOutput $OllamaOutLog `
        -RedirectStandardError $OllamaErrLog `
        -PassThru

    Write-Host "Started Ollama process $($OllamaProcess.Id). Waiting for the local API..."

    if (Wait-OllamaApi -TimeoutSeconds $OllamaWaitSeconds) {
        Write-Host "Ollama is running with OLLAMA_CONTEXT_LENGTH=$env:OLLAMA_CONTEXT_LENGTH."
    }
    else {
        Write-Warning "Ollama did not respond within $OllamaWaitSeconds seconds."
        Write-Warning "Streamlit will still start. In the app, click Refresh models after Ollama is ready."
        Write-Warning "Ollama logs: $OllamaOutLog and $OllamaErrLog"
    }
}

Write-Host "Starting CourseScope..."
& $VenvPython -m streamlit run $AppFile
