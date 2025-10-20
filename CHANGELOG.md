## [Unreleased]

### Added
- 

### Changed
- 

### Fixed
- 

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
## 2025-10-20 – Hardening
- Docs: unificação de README/CHANGELOG; duplicatas movidas para docs/_duplicates.
- README: corrigida citação para epieratti/funkbr-lyrics-evolution.
- Health: warning automático para JSONL 0 bytes após janela de coleta.
- Backup: registrar caminho no Drive + SHA256 em cada snapshot.

- Snapshot: data/raw/one_20251020_010051_Anitta_albums_tracks.jsonl
  - SHA256: c51e73993dbcd965230f6c6223d6d08ea90c7ff94ac79ca3dfb5eeaccebb84b5
  - Drive:  gdrive:Backups/funkbr-lyrics-evolution/one_20251020_010051_Anitta_albums_tracks.jsonl


[Unreleased]: https://github.com/epieratti/funkbr-lyrics-evolution/compare/v1.0.0-alpha...HEAD
