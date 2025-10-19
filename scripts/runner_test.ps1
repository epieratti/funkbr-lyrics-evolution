# RUNNER DE TESTE — FUNKBR-LYRICS-EVOLUTION
# Executa o coletor v11f com .env_test e abre o monitor ASCII.
# Versão "limpa" e compatível com PowerShell 5/7.

# --- Config ---
$ErrorActionPreference = "Stop"
$envFile = ".\env_test"
$collectorScript = ".\coletar_discografia_funk_br_v11f.py"
$monitorScript = ".\monitor_progress_ascii.ps1"
$progressFile = "logs\collector_test_part2_progress.json"

# --- Helpers ---
function Load-DotEnv {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Host "Arquivo de ambiente nao encontrado: $Path"
        exit 1
    }
    Get-Content -LiteralPath $Path | ForEach-Object {
        if ($_ -match '^\s*#') { return }
        if ($_ -match '^\s*$') { return }
        if ($_ -match '^(?<k>[^=]+)=(?<v>.*)$') {
            $k = $matches.k.Trim()
            $v = $matches.v.Trim()
            if ($v.StartsWith('"')) {
                $v = $v -replace '^"', ''
                $v = $v -replace '"\s*(#.*)?$', ''
            } else {
                $v = $v -replace '\s*(#.*)?$', ''
            }
            Set-Item -Path ("Env:{0}" -f $k) -Value $v
        }
    }
}

function Ensure-File {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Host "Arquivo necessario nao encontrado: $Path"
        exit 1
    }
}

# --- Execucao ---
Load-DotEnv -Path $envFile

Ensure-File -Path $collectorScript
Ensure-File -Path $monitorScript

if (-not (Test-Path -LiteralPath (Split-Path -Parent $progressFile))) {
    New-Item -Type Directory -Path (Split-Path -Parent $progressFile) | Out-Null
}

Write-Host "SEED_FILE=$($env:SEED_FILE)"
Write-Host "OUTPUT_JSONL=$($env:OUTPUT_JSONL)"
Write-Host "LOG_FILE=$($env:LOG_FILE)"
Write-Host "PROGRESS_FILE=$($env:PROGRESS_FILE)"

# Inicia coletor (janela atual)
Start-Process -NoNewWindow -FilePath "python" -ArgumentList $collectorScript

# Abre monitor em nova janela PowerShell (sem usar & nem escaping complexo)
Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy","Bypass",
    "-File", $monitorScript,
    "-ProgressFile", $progressFile,
    "-RefreshSec","3"
)

Write-Host "Coletor iniciado e monitor aberto."