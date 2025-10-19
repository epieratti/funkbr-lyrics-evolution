# Runner sequencial com retries e logs
param(
  [string]$First = "2",
  [string]$Last = "12"
)

$ErrorActionPreference = "Stop"

# Configs globais
$env:INCLUDE_RELATED="0"
$env:SLEEP_BETWEEN_CALLS="0.3"
$env:BACKOFF_START="1.5"
$env:TIMEOUT_S="120"
$env:FLUSH_EVERY_N_ROWS="500"
$logFile = "runner_log.txt"

"=== Inicio do runner: $(Get-Date) ===" | Out-File $logFile -Encoding utf8

function Run-Block($i, $attempt) {
  Write-Host ">>> Rodando bloco $i tentativa $attempt..." -ForegroundColor Yellow
  $env:SEED_FILE = "seed_part_${i}.txt"
  $env:OUTPUT_JSONL = "raw_part_${i}.jsonl"
  $env:OUTPUT_CSV = "funk_br_discografia_part_${i}.csv"
  $env:PROGRESS_FILE = "collector_progress_${i}.json"
  $env:LOG_FILE = "collector_log_${i}.txt"
  py .\coletar_discografia_funk_br.py
  return $LASTEXITCODE
}

# loop
$start = [int]$First
$end = [int]$Last
for ($i = $start; $i -le $end; $i++) {
  $ok = $false
  for ($t = 1; $t -le 2; $t++) {
    try {
      $exit = Run-Block $i $t
      if ($exit -eq 0) {
        $ok = $true
        "Bloco $i finalizado com sucesso em $(Get-Date)" | Out-File $logFile -Append -Encoding utf8
        break
      } else {
        "Bloco $i falhou exitcode $exit em $(Get-Date) nova tentativa" | Out-File $logFile -Append -Encoding utf8
        Start-Sleep -Seconds 10
      }
    } catch {
      # IMPORTANT: use -f to avoid $t: parsing as a scope marker
      ("Excecao no bloco {0} tentativa {1}: {2}" -f $i, $t, $_.Exception.Message) | Out-File $logFile -Append -Encoding utf8
      Start-Sleep -Seconds 10
    }
  }
  if (-not $ok) {
    "Bloco $i falhou definitivamente em $(Get-Date)" | Out-File $logFile -Append -Encoding utf8
  }
  Start-Sleep -Seconds 4
}

# merge final
Write-Host ">>> Fazendo merge final..." -ForegroundColor Yellow
$mergePy = @"
import os, glob, pandas as pd
arquivos = sorted(glob.glob('funk_br_discografia_part_*.csv'))
dfs = []
for f in arquivos:
    try:
        if os.path.getsize(f) > 0:
            df = pd.read_csv(f, dtype={'track_id': str})
            if not df.empty:
                dfs.append(df)
    except Exception:
        pass
if dfs:
    df = pd.concat(dfs, ignore_index=True)
    if 'track_id' in df.columns:
        df = df.drop_duplicates(subset=['track_id'])
    df = df.sort_values(['release_year','popularity','track_name'], ascending=[True,False,True], na_position='last')
    df.to_csv('funk_br_discografia_ALL.csv', index=False, encoding='utf-8')
    print('OK | funk_br_discografia_ALL.csv |', len(df), 'linhas a partir de', len(arquivos), 'arquivos')
else:
    print('Nenhum CSV encontrado para merge.')
"@
Set-Content -Path ".\merge_runner.py" -Value $mergePy -Encoding UTF8
py .\merge_runner.py
"=== Runner finalizado: $(Get-Date) ===" | Out-File $logFile -Append -Encoding utf8
Write-Host ">>> Runner finalizado. Confira funk_br_discografia_ALL.csv e runner_log.txt" -ForegroundColor Cyan
