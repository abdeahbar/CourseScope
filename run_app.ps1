$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AppFile = Join-Path $ProjectRoot "app.py"
$OllamaApiUrl = "http://127.0.0.1:11434/api/tags"
$OllamaWaitSeconds = 90
$LLAMA_SERVER_PATH = ".\llama.cpp\llama-server.exe"
$LLAMA_MODEL_PATH = ".\models\model.gguf"
$LLAMA_PORT = 8080
$START_LLAMA_CPP = $false
$LlamaCppWaitSeconds = 60
$LlamaCppApiUrl = "http://127.0.0.1:$LLAMA_PORT/v1/models"
$OutputPath = Join-Path $ProjectRoot "output"
$OllamaOutLog = Join-Path $OutputPath "ollama-stdout.log"
$OllamaErrLog = Join-Path $OutputPath "ollama-stderr.log"
$LlamaCppOutLog = Join-Path $OutputPath "llamacpp-stdout.log"
$LlamaCppErrLog = Join-Path $OutputPath "llamacpp-stderr.log"
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

function Resolve-ProjectPath {
    param (
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return Join-Path $ProjectRoot $Path
}

function Test-LlamaCppApi {
    try {
        Invoke-RestMethod -Uri $LlamaCppApiUrl -Method Get -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-LlamaCppApi {
    param (
        [int]$TimeoutSeconds
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        if (Test-LlamaCppApi) {
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

if ($START_LLAMA_CPP) {
    $LlamaServerFullPath = Resolve-ProjectPath $LLAMA_SERVER_PATH
    $LlamaModelFullPath = Resolve-ProjectPath $LLAMA_MODEL_PATH

    if (Test-LlamaCppApi) {
        Write-Host "llama.cpp server is already running on port $LLAMA_PORT."
    }
    elseif (-not (Test-Path $LlamaServerFullPath)) {
        Write-Warning "llama.cpp server was not found at: $LlamaServerFullPath"
    }
    elseif (-not (Test-Path $LlamaModelFullPath)) {
        Write-Warning "GGUF model was not found at: $LlamaModelFullPath"
    }
    else {
        Write-Host "Starting llama.cpp server..."
        New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null

        $LlamaArguments = @(
            "-m", $LlamaModelFullPath,
            "--host", "127.0.0.1",
            "--port", "$LLAMA_PORT",
            "-c", "4096",
            "-ngl", "99",
            "--flash-attn"
        )

        $LlamaProcess = Start-Process `
            -FilePath $LlamaServerFullPath `
            -ArgumentList $LlamaArguments `
            -WindowStyle Hidden `
            -RedirectStandardOutput $LlamaCppOutLog `
            -RedirectStandardError $LlamaCppErrLog `
            -PassThru

        Write-Host "Started llama.cpp process $($LlamaProcess.Id). Waiting for the local API..."

        if (Wait-LlamaCppApi -TimeoutSeconds $LlamaCppWaitSeconds) {
            Write-Host "llama.cpp server is running on port $LLAMA_PORT."
        }
        else {
            Write-Warning "llama.cpp did not respond within $LlamaCppWaitSeconds seconds."
            Write-Warning "Streamlit will still start. llama.cpp logs: $LlamaCppOutLog and $LlamaCppErrLog"
        }
    }
}

Write-Host "Starting CourseScope..."
& $VenvPython -m streamlit run $AppFile
