# monitor_progress_ascii.ps1 — monitor simples, compatível com Windows (ASCII)
param(
  [string]$ProgressFile = "logs/collector_test_part2_progress.json",
  [int]$RefreshSec = 3
)

function Bar([double]$pct){
  if ($pct -lt 0) { $pct = 0 }
  if ($pct -gt 1) { $pct = 1 }
  $w = 30
  $fill = [int]([math]::Round($pct * $w))
  $empty = $w - $fill
  $hashes = "#" * $fill
  $dashes = "-" * $empty
  "{0}{1}{2}{3}" -f "[", $hashes, $dashes, ("] " + ("{0:P0}" -f $pct))
}

Write-Host "Monitor de Progresso (Ctrl+C para sair)"
Write-Host ("Lendo: {0}" -f $ProgressFile)
Write-Host ""

while ($true) {
  try {
    if (-not (Test-Path -Path $ProgressFile)) {
      Write-Host "(aguardando arquivo de progresso...)"
      Start-Sleep -Seconds $RefreshSec
      continue
    }

    $raw = Get-Content -Path $ProgressFile -Raw -ErrorAction Stop
    if (-not $raw) {
      Start-Sleep -Seconds $RefreshSec
      continue
    }

    $json = $raw | ConvertFrom-Json

    Clear-Host
    Write-Host "=== FunkBR Coleta - Progresso ==="
    Write-Host ("Atualizado: {0}" -f (Get-Date))
    Write-Host ""

    # Cabecalho de auditoria (ASCII)
    if ($json.run_id) { Write-Host ("run_id: {0}" -f $json.run_id) }
    if ($json.started_at -and $json.updated_at) {
      Write-Host ("started_at: {0}   updated_at: {1}" -f $json.started_at, $json.updated_at)
    }
    if ($json.inputs) {
      Write-Host ("seed: {0}" -f $json.inputs.seed_file_path)
      if ($json.inputs.seed_file_sha256) { Write-Host ("seed_sha256: {0}" -f $json.inputs.seed_file_sha256) }
    }
    Write-Host ("git: {0}   schema: {1}   script: {2}" -f $json.git_commit, $json.schema_version, $json.script_version)
    Write-Host ""

    # Metricas de qualidade e rede
    if ($null -ne $json.dedupe_seen_count -or $null -ne $json.skipped_out_of_range) {
      Write-Host ("dedupe_seen: {0}   skipped_out_of_range: {1}" -f $json.dedupe_seen_count, $json.skipped_out_of_range)
    }
    if ($null -ne $json.appears_on_kept -or $null -ne $json.appears_on_dropped_by_cap) {
      Write-Host ("appears_on kept/dropped: {0}/{1}" -f $json.appears_on_kept, $json.appears_on_dropped_by_cap)
    }
    if ($json.http_counts) {
      Write-Host ("HTTP 200/429/5xx: {0}/{1}/{2}   retries: {3}" -f $json.http_counts.'200', $json.http_counts.'429', $json.http_counts.'5xx', $json.retry_count_total)
    }
    Write-Host ""

    # Progresso por artista / album / faixa
    switch ($json.stage) {
      "start" {
        $aTotal = [int]$json.artists_total
        $aIdx = [int]$json.artist_index
        $pctA = if ($aTotal -gt 0) { $aIdx / $aTotal } else { 0 }
        Write-Host ("Artistas: {0}/{1}  {2}" -f $aIdx, $aTotal, (Bar $pctA))
      }
      "artist" {
        $aTotal = [int]$json.artists_total
        $aIdx = [int]$json.artist_index
        $pctA = if ($aTotal -gt 0) { $aIdx / $aTotal } else { 0 }
        Write-Host ("Artista:  {0} ({1}/{2})  {3}" -f $json.artist_name, $aIdx, $aTotal, (Bar $pctA))
        if ($json.written_so_far -ne $null) { Write-Host ("Escritas ate agora: {0}" -f $json.written_so_far) }
      }
      "albums_primary" {
        $done = [int]$json.albums_done
        $tot  = [int]$json.albums_total
        $pct  = if ($tot -gt 0) { $done / $tot } else { 0 }
        Write-Host ("Albuns (album,single): {0}/{1}  {2}" -f $done, $tot, (Bar $pct))
      }
      "albums_appears" {
        $done = [int]$json.albums_done
        $tot  = [int]$json.albums_total
        $pct  = if ($tot -gt 0) { $done / $tot } else { 0 }
        Write-Host ("Albuns (appears_on):  {0}/{1}  {2}" -f $done, $tot, (Bar $pct))
      }
      "album_tracks" {
        $ti = [int]$json.track_index
        $tt = [int]$json.tracks_total
        $pctT = if ($tt -gt 0) { $ti / $tt } else { 0 }
        Write-Host ("Album:  {0} ({1})" -f $json.album_name, $json.release_year)
        Write-Host ("Faixas: {0}/{1}  {2}" -f $ti, $tt, (Bar $pctT))
        if ($json.albums_total -ge 0) {
          $adone = [int]$json.albums_done
          $atot  = [int]$json.albums_total
          $pca   = if ($atot -gt 0) { $adone / $atot } else { 0 }
          Write-Host ("Albuns do grupo: {0}/{1}  {2}" -f $adone, $atot, (Bar $pca))
        }
      }
      "jsonl_done" {
        Write-Host ("JSONL concluido. Linhas: {0}" -f $json.rows)
      }
      "done" {
        Write-Host ("FINALIZADO - linhas: {0}" -f $json.rows)
        if ($json.elapsed_min -ne $null) { Write-Host ("Tempo (min): {0}" -f $json.elapsed_min) }
      }
      default {
        Write-Host ("Stage: {0}" -f $json.stage)
      }
    }

    # Stages (resumo)
    if ($json.stages) {
      Write-Host ""
      Write-Host "Etapas:"
      foreach ($s in $json.stages) {
        $ok = if ($s.ok -eq $true) { "[OK]" } elseif ($s.ok -eq $false) { "[X]" } else { "[...]" }
        Write-Host ("{0} {1}  {2} -> {3}" -f $ok, $s.name, $s.t_start, $s.t_end)
      }
    }

  } catch {
    Write-Host ("Erro ao ler progresso: {0}" -f $_.Exception.Message)
  }
  Start-Sleep -Seconds $RefreshSec
}
