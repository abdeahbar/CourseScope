param (
    [string]$LlamaServerPath = ".\llama.cpp\llama-server.exe",
    [string]$ModelPath = "",
    [switch]$DownloadTinyModel,
    [int]$Port = 18080,
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$OutputPath = Join-Path $ProjectRoot "output"
$TinyModelUrl = "https://huggingface.co/ggml-org/tiny-llamas/resolve/main/stories260K.gguf"
$TinyModelPath = Join-Path $ProjectRoot ".cache\llamacpp-smoke\stories260K.gguf"
$LlamaCppOutLog = Join-Path $OutputPath "llamacpp-smoke-stdout.log"
$LlamaCppErrLog = Join-Path $OutputPath "llamacpp-smoke-stderr.log"
$BaseUrl = "http://127.0.0.1:$Port"
$ModelsUrl = "$BaseUrl/v1/models"
$ChatUrl = "$BaseUrl/v1/chat/completions"

function Resolve-ProjectPath {
    param (
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return $Path
    }

    return Join-Path $ProjectRoot $Path
}

function Wait-LlamaCppApi {
    param (
        [int]$TimeoutSeconds
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        try {
            Invoke-RestMethod -Uri $ModelsUrl -Method Get -TimeoutSec 2 | Out-Null
            return $true
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    return $false
}

function Get-DefaultModel {
    $ModelsPath = Join-Path $ProjectRoot "models"

    if (-not (Test-Path $ModelsPath)) {
        return $null
    }

    return Get-ChildItem -Path $ModelsPath -Filter "*.gguf" -File |
        Sort-Object Name |
        Select-Object -First 1
}

$ServerFullPath = Resolve-ProjectPath $LlamaServerPath
if (-not (Test-Path $ServerFullPath)) {
    Write-Error "llama-server.exe was not found at: $ServerFullPath. Run .\setup_llamacpp.ps1 first."
}

New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null

if ([string]::IsNullOrWhiteSpace($ModelPath)) {
    if ($DownloadTinyModel) {
        if (-not (Test-Path $TinyModelPath)) {
            Write-Host "Downloading tiny GGUF smoke-test model..."
            New-Item -ItemType Directory -Force -Path (Split-Path $TinyModelPath -Parent) | Out-Null
            Invoke-WebRequest -Uri $TinyModelUrl -OutFile $TinyModelPath
        }
        $ModelFullPath = $TinyModelPath
    }
    else {
        $DefaultModel = Get-DefaultModel
        if (-not $DefaultModel) {
            Write-Error "No GGUF model was found. Add one to .\models, pass -ModelPath, or run .\test_llamacpp.ps1 -DownloadTinyModel."
        }
        $ModelFullPath = $DefaultModel.FullName
    }
}
else {
    $ModelFullPath = Resolve-ProjectPath $ModelPath
}

if (-not (Test-Path $ModelFullPath)) {
    Write-Error "GGUF model was not found at: $ModelFullPath"
}

try {
    Invoke-RestMethod -Uri $ModelsUrl -Method Get -TimeoutSec 2 | Out-Null
    Write-Error "A llama.cpp server is already responding on port $Port. Choose another -Port for the smoke test."
}
catch {
    # Expected: the smoke test starts its own temporary server.
}

$ModelAlias = [System.IO.Path]::GetFileName($ModelFullPath)
$LlamaArguments = @(
    "-m", $ModelFullPath,
    "--host", "127.0.0.1",
    "--port", "$Port",
    "--alias", $ModelAlias,
    "-c", "512",
    "-ngl", "0",
    "--flash-attn", "off"
)

Write-Host "Starting temporary llama.cpp server on port $Port..."
$LlamaProcess = Start-Process `
    -FilePath $ServerFullPath `
    -ArgumentList $LlamaArguments `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LlamaCppOutLog `
    -RedirectStandardError $LlamaCppErrLog `
    -PassThru

try {
    if (-not (Wait-LlamaCppApi -TimeoutSeconds $TimeoutSeconds)) {
        Write-Error "llama.cpp did not respond within $TimeoutSeconds seconds. Logs: $LlamaCppOutLog and $LlamaCppErrLog"
    }

    $Payload = @{
        model = $ModelAlias
        messages = @(
            @{
                role = "system"
                content = "Return only valid JSON."
            },
            @{
                role = "user"
                content = "Return a JSON object with one boolean key named ok set to true."
            }
        )
        temperature = 0
        max_tokens = 32
        response_format = @{
            type = "json_object"
        }
    } | ConvertTo-Json -Depth 6

    $Response = Invoke-RestMethod `
        -Uri $ChatUrl `
        -Method Post `
        -ContentType "application/json" `
        -Body $Payload `
        -TimeoutSec $TimeoutSeconds

    $Content = $Response.choices[0].message.content
    if ([string]::IsNullOrWhiteSpace($Content)) {
        Write-Error "llama.cpp returned an empty chat completion response."
    }

    $ParseContent = $Content.Trim()
    if ($ParseContent.StartsWith('```')) {
        $ParseContent = $ParseContent -replace '^```(?:json)?\s*', ''
        $ParseContent = $ParseContent -replace '\s*```$', ''
    }

    $JsonStatus = "valid JSON"
    try {
        $Parsed = $ParseContent | ConvertFrom-Json
        if ($null -eq $Parsed) {
            $JsonStatus = "not JSON"
        }
    }
    catch {
        $JsonStatus = "not JSON"
    }

    Write-Host "llama.cpp smoke test passed."
    Write-Host "Model: $ModelFullPath"
    Write-Host "Response parse: $JsonStatus"
    Write-Host "Response: $Content"
}
finally {
    if ($LlamaProcess -and -not $LlamaProcess.HasExited) {
        Stop-Process -Id $LlamaProcess.Id -Force
        $LlamaProcess.WaitForExit()
    }
}
