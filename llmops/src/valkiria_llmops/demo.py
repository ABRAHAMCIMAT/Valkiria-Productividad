"""Evaluación de ejemplo de F0: validez de JSON sobre el dataset ``formato`` v1.

No usa ningún LLM: comprueba la cadena run etiquetado → gate → exportación (CA-03.1).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from valkiria_llmops import __version__
from valkiria_llmops import tags as tg

DATASET = Path(__file__).resolve().parents[2] / "datasets" / "formato" / "v1.jsonl"
UMBRAL_JSON_VALIDO = 1.0  # docs/05 §3: formato JSON válido = 1.00


def json_valido(texto: str) -> bool:
    try:
        json.loads(texto)
    except ValueError:
        return False
    return True


def evaluar(casos: list[dict[str, str]]) -> dict[str, float]:
    validos = sum(json_valido(c["salida"]) for c in casos)
    return {"json_valido": validos / len(casos) if casos else 0.0, "casos": float(len(casos))}


def ejecutar(
    mlflow: Any, *, fase: str, hu: str, dataset: Path = DATASET, sha: str | None = None
) -> str:
    """Registra un run en ``formato-eval`` con los tags obligatorios y devuelve su ``run_id``."""
    contenido = dataset.read_bytes()
    casos = [json.loads(linea) for linea in contenido.decode("utf-8").splitlines() if linea.strip()]
    metricas = evaluar(casos)
    etiquetas = tg.construir(
        phase=fase,
        hu=hu,
        model_sha256=hashlib.sha256(contenido).hexdigest(),
        prompts={"formato": 1},
        profile="ci",
        valkiria_version=__version__,
        sha=sha,
        extra={"model.name": "fixture-formato-v1", "dataset": "formato@v1"},
    )
    mlflow.set_experiment("formato-eval")
    with mlflow.start_run(run_name=f"formato-{fase}", tags=etiquetas) as run:
        mlflow.log_params({"dataset": "formato@v1", "umbral.json_valido": UMBRAL_JSON_VALIDO})
        mlflow.log_metrics(metricas)
        mlflow.set_tag(
            "gate.formato", "pass" if metricas["json_valido"] >= UMBRAL_JSON_VALIDO else "fail"
        )
        return str(run.info.run_id)
