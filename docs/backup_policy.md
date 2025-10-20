# Política de Backup — FunkBR

Frequência
- Backup automático diário às 06h30 UTC
- Backup semanal consolidado (segunda-feira)

Destinos
- Google Drive: gdrive:Backups/funkbr-lyrics-evolution
- GitHub: epieratti/funkbr-lyrics-evolution

Retenção
- Diários: 7 dias
- Semanais: 2 meses
- Mensais: 12 meses

Verificação
- Cada snapshot deve possuir hash SHA256 registrado no health
- Divergências geram alerta manual

Restauração
- Restore local via rclone copy
- Restore histórico via git tags, ex: v0.9-pre-release
