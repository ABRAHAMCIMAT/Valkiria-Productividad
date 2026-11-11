# Valkiria LLMOps

Herramientas de LLMOps de Valkiria sobre **MLflow 3** ([ADR-0005](../docs/adr/ADR-0005-llmops-mlflow.md),
[05 · LLMOps](../docs/05-llmops-trazabilidad.md)).

```bash
cd llmops
uv sync --all-groups
uv run llmops serve                      # MLflow en http://127.0.0.1:5000 (solo loopback, RN-03.3)
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
uv run llmops bootstrap                  # crea los experimentos base (idempotente)
uv run llmops demo-eval --phase F0 --hu HU-03
uv run llmops gate --phase F0            # falla si algún run no tiene los tags obligatorios
uv run llmops export --phase F0          # evidencias/F0/mlflow/<run>.json + manifest.sha256
```

Los datos de MLflow se guardan en `~/.valkiria/mlflow/` (`VALKIRIA_MLFLOW_HOME` para cambiarlo).
