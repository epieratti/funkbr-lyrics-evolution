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

---

## Restore baseline (rclone)

Passos mínimos e reprodutíveis para restaurar do Google Drive:

1) Verifique o remote configurado:
    rclone listremotes

2) Descubra o snapshot mais recente (somente .tar.gz):
    LATEST_SNAPSHOT="$(rclone lsf gdrive:Backups/funkbr-lyrics-evolution --files-only \
      | grep -E '\.tar\.gz$' | sort | tail -n1)"
    echo "LATEST_SNAPSHOT = $LATEST_SNAPSHOT"

3) Baixe para um diretório de restore:
    RESTORE_DIR="/restore"
    mkdir -p "$RESTORE_DIR"
    rclone copy "gdrive:Backups/funkbr-lyrics-evolution/${LATEST_SNAPSHOT}" "$RESTORE_DIR" \
      --progress --fast-list

4) Extraia o snapshot:
    tar -xzf "${RESTORE_DIR}/${LATEST_SNAPSHOT}" -C "$RESTORE_DIR"

5) (Opcional) Inspecione conteúdo restaurado:
    find "$RESTORE_DIR" -maxdepth 2 -type f -printf "%P\t%k KB\n" | head -n 30

Notas:
- Requer `rclone` previamente autenticado com o remote `gdrive`.
- Use `timeout 10s rclone ... || echo "[warn] timeout"` se quiser evitar travas.
- Em produção, prefira restaurar para um diretório limpo.
