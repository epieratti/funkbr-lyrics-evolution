# Changelog — FunkBR Lyrics Evolution

## [v0.1.0] — 2025-10-20
### 🚀 Release inicial estável
- Cron jobs com locks (`scripts/with_lock.sh`) ativos:
  - `make collect` → 02:00  
  - `make lyrics`  → 04:00  
  - `make process sanity` → 06:00
- Hook `usercustomize.py`: gravação atômica e bloqueio de `.jsonl` vazios
- Backup automático (tar.gz + hash SHA256)
- Health-check agendado em `reports/health/`
- Make targets padronizados:
  - `collect`, `lyrics`, `process sanity`, `health`
- Pipeline validado com `run_pilot.py` e `make sanity`

---

> 📦 Snapshot de backup:  
> `/mnt/backup/funkbr_repo_2025-10-20_0656.tar.gz`  
> SHA256: `1986effbf03dec8f232142468579600e9da1265275f01b1145508cd1059c5d5a`
