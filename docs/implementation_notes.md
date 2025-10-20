# Notas de Implementação — Health Reports (diagnóstico)

## Objetivo
Avaliar unificação opcional dos health reports em um único artefato diário,
sem alterar o comportamento atual.

## Varredura de dependências (grep)
```bash
scripts/health_warning_gate.sh:5:#   HEALTH_STRICT=true ./scripts/health_warning_gate.sh --data-dir data/raw --window-end "06:30"
scripts/health_warning_gate.sh:11:# Saída: escreve um arquivo reports/health/health_YYYY-MM-DD_HHMM.txt e printa no stdout.
scripts/health_warning_gate.sh:35:OUT_DIR="reports/health"
scripts/health_warning_gate.sh:36:OUT_FILE="${OUT_DIR}/health_${STAMP}.txt"
scripts/health_today_summary.sh:4:scripts/health_zero_byte_guard.sh data/raw || true
scripts/diag/install_health_suite.sh:6:# 1.1 health_diag principal
scripts/diag/install_health_suite.sh:7:cat > "$ROOT/scripts/diag/health_diag.sh" <<'EOT'
scripts/diag/install_health_suite.sh:139:# 1.9 runner único de health
scripts/diag/install_health_suite.sh:140:cat > "$ROOT/scripts/diag/run_full_health.sh" <<'EOT'
scripts/diag/install_health_suite.sh:144:bash "$ROOT/scripts/diag/health_diag.sh" "$ROOT"
scripts/diag/install_health_suite.sh:156:echo "Instalador criado em scripts/diag/install_health_suite.sh"
scripts/diag/run_full_health.sh:4:bash "$ROOT/scripts/diag/health_diag.sh" "$ROOT"
scripts/apply_project_hardening.sh:7:mkdir -p docs logs reports/health code crontab scripts
scripts/apply_project_hardening.sh:66:# --- Health imediato (log em reports/health/)
scripts/apply_project_hardening.sh:68:mkdir -p reports/health
scripts/apply_project_hardening.sh:69:( set +e; END_HOUR_LOCAL="${END_HOUR_LOCAL:-06}" scripts/health_zero_byte_guard.sh data/raw || true ) \
scripts/apply_project_hardening.sh:70:  | tee "reports/health/health_${ts}.txt" >/dev/null
scripts/apply_project_hardening.sh:100:  if ! grep -qE '^health:' Makefile; then
scripts/apply_project_hardening.sh:103:health:
scripts/apply_project_hardening.sh:104:	@END_HOUR_LOCAL=06 scripts/health_zero_byte_guard.sh data/raw || true
scripts/apply_project_hardening.sh:105:	@echo "Relatório em reports/health/"
scripts/apply_project_hardening.sh:107:sanity: health
Makefile:48:health: ## checa cron, logs de hoje, jsonl e backup
Makefile:53:	@END_HOUR_LOCAL=06 scripts/health_zero_byte_guard.sh data/raw || true
Makefile:245:		scripts/diag/run_full_health.sh \
```

## Observações (proposta não aplicada)
- Mantido **status quo**: nenhuma mudança em scripts/cron/logrotate.
- Unificação exigiria:
  - Ajustar `scripts/diag/run_full_health.sh` para escrever sempre em um
    caminho único (ex.: `logs/health_$(date +%F).log`) **e** opcionalmente
    emitir um snapshot JSON (`logs/health_$(date +%F).json`).
  - Revisar `logrotate` para não conflitar com nomes consolidados.
- Como o ambiente já registra `logs/health_YYYY-MM-DD.log` via cron
  em `/etc/cron.d/funkbr_health`, a “unificação” prática já ocorre por dia.
  **Impeditivo leve**: padronizar eventuais saídas auxiliares (JSON/CSV)
  exigiria pequena refatoração do script de health.
- Decisão: **não alterar nada nesta branch** (escopo solicitado: apenas
  avaliação). Proposta de follow-up: PR dedicado com flag `--json-out`.

