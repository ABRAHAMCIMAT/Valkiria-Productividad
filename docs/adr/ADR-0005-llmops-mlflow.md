# ADR-0005 · Framework LLMOps: MLflow 3 autoalojado

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Contexto
Se necesita un framework LLMOps open source que funcione en una laptop y que cubra tracing, versionado de prompts, evaluación y registro de modelos, con evidencia auditable por fase.

## Decisión
**MLflow 3** (Apache 2.0) con *backend store* SQLite y artefactos locales, usado para:
- Tracing: `mlflow.langchain.autolog()`, compatible con OpenTelemetry.
- **Prompt Registry**, con los alias `@candidate` y `@production`.
- `mlflow.genai.evaluate` con scorers.
- LoggedModel y registro de modelos.

Se complementa con Ragas y DeepEval (métricas), y con promptfoo y garak (red team).

## Alternativas
- **Langfuse:** MIT en su núcleo, pero requiere PostgreSQL, ClickHouse, Redis y S3, lo cual es pesado para una laptop. Queda como opción para el modo equipo.
- **Arize Phoenix:** licencia ELv2, que no es OSI.
- **LangSmith:** propietario.

## Consecuencias
- (+) Un solo proceso ligero, con exportación JSON como evidencia de fase.
- (−) Las métricas con un LLM juez local requieren calibración humana (riesgo R-06).
