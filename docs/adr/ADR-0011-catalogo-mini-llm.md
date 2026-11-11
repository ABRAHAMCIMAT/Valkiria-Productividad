# ADR-0011 · Catálogo de mini LLMs gratuitos

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
- Solo modelos de **14 B parámetros o menos**, con licencia **Apache 2.0 o MIT** (otra licencia requiere un ADR específico), en formato GGUF, MLX u ONNX, y con SHA-256 registrado en `llmops/models/catalog.yaml`.
- Candidatos iniciales (ver [02 · §4](../02-revision-arquitectura-azure.md#4-catálogo-de-mini-llms-gratuitos)):
  - Principales: Qwen3 4B/8B/14B, Phi-4-mini, Granite y SmolLM3.
  - Router: Qwen3 0.6B/1.7B.
  - Visión: Qwen3-VL 4B/8B.
  - Embeddings: e5-small y bge-m3.
  - Re-ranker: bge-reranker-v2-m3.
  - Voz: whisper.
- **La elección por perfil la decide el benchmark de F1 (HU-06)**, y este ADR se actualiza con los `run_id` de MLflow que la respaldan.

## Pendiente (se completa en el cierre de F1)
| Perfil | Principal | Router | run_id |
|---|---|---|---|
| Estándar | _por definir_ | _por definir_ | _por definir_ |
| Avanzado | _por definir_ | _por definir_ | _por definir_ |
