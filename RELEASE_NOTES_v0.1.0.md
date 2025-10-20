## v0.1.0 — release inicial estável
- Cron jobs com locks (`scripts/with_lock.sh`) configurados: coletar 02:00, lyrics 04:00, process+sanity 06:00
- Hook `usercustomize.py`: evita `.jsonl` vazios (escrita atômica)
- Backup e health-check agendados
- Make targets: `collect`, `lyrics`, `process sanity`, `health`
- Pilot runner: geração de `data/raw/funk_br_discografia_raw_<SNAPSHOT>.jsonl`
