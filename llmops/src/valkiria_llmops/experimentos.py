"""Experimentos base de MLflow (docs/05 §2)."""

from __future__ import annotations

from typing import Any

EXPERIMENTOS: dict[str, str] = {
    "model-selection": "Benchmark de calidad, TTFT, tok/s y RAM por modelo y perfil (F1)",
    "rag-eval": "Evaluación de RAG: faithfulness, recall de contexto y citas (F3)",
    "tools-eval": "Llamadas a herramientas correctas e inventadas (F4)",
    "router-eval": "Exactitud del router de intención (F4)",
    "redteam": "promptfoo y garak: tasa de éxito de ataques (F5)",
    "perf-bench": "Rendimiento: TTFT p95, tok/s y RAM máxima",
    "formato-eval": "Validez del formato de salida estructurada (JSON)",
}


def asegurar(cliente: Any) -> dict[str, str]:
    """Crea los experimentos que falten (idempotente) y devuelve ``nombre -> experiment_id``."""
    ids: dict[str, str] = {}
    for nombre, descripcion in EXPERIMENTOS.items():
        exp = cliente.get_experiment_by_name(nombre)
        if exp is None:
            ids[nombre] = cliente.create_experiment(
                nombre, tags={"mlflow.note.content": descripcion, "valkiria.base": "true"}
            )
        else:
            ids[nombre] = exp.experiment_id
    return ids
