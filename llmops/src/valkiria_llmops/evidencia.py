"""Gate de fase y exportación de runs como evidencia (CA-03.2, CA-03.3, docs/05 §5)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from valkiria_llmops import tags as tg

MANIFIESTO = "manifest.sha256"


@dataclass(frozen=True, slots=True)
class Hallazgo:
    run_id: str
    experimento: str
    problema: str

    def __str__(self) -> str:
        return f"run {self.run_id} ({self.experimento}): {self.problema}"


def runs_de_fase(cliente: Any, fase: str) -> list[tuple[str, Any]]:
    """Runs de todos los experimentos con ``tags.phase = fase``, como ``(experimento, run)``."""
    resultado = []
    for exp in cliente.search_experiments():
        for run in cliente.search_runs(
            [exp.experiment_id], filter_string=f"tags.phase = '{fase}'", max_results=10_000
        ):
            resultado.append((exp.name, run))
    return resultado


def gate(cliente: Any, fase: str) -> tuple[int, list[Hallazgo]]:
    """Valida los tags de cada run de la fase. Devuelve ``(runs revisados, hallazgos)``."""
    runs = runs_de_fase(cliente, fase)
    hallazgos = [
        Hallazgo(run.info.run_id, nombre, p)
        for nombre, run in runs
        for p in tg.faltantes(run.data.tags)
    ]
    return len(runs), hallazgos


def _run_a_dict(experimento: str, run: Any) -> dict[str, Any]:
    info = run.info
    return {
        "run_id": info.run_id,
        "experimento": experimento,
        "nombre": info.run_name,
        "estado": info.status,
        "inicio_ms": info.start_time,
        "fin_ms": info.end_time,
        "tags": {k: v for k, v in sorted(run.data.tags.items()) if not k.startswith("mlflow.")},
        "params": dict(sorted(run.data.params.items())),
        "metricas": dict(sorted(run.data.metrics.items())),
    }


def exportar(cliente: Any, fase: str, destino: Path) -> list[Path]:
    """Escribe un JSON por run en ``destino/mlflow/`` y regenera el manifiesto del paquete."""
    carpeta = destino / "mlflow"
    carpeta.mkdir(parents=True, exist_ok=True)
    escritos = []
    for nombre, run in runs_de_fase(cliente, fase):
        ruta = carpeta / f"{run.info.run_id}.json"
        ruta.write_text(
            json.dumps(_run_a_dict(nombre, run), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        escritos.append(ruta)
    manifiesto(destino)
    return escritos


def manifiesto(raiz: Path) -> Path:
    """Genera ``manifest.sha256`` (formato ``sha256sum``) con todos los archivos bajo ``raiz``."""
    lineas = []
    for archivo in sorted(p for p in raiz.rglob("*") if p.is_file() and p.name != MANIFIESTO):
        digest = hashlib.sha256(archivo.read_bytes()).hexdigest()
        lineas.append(f"{digest}  {archivo.relative_to(raiz).as_posix()}")
    ruta = raiz / MANIFIESTO
    ruta.write_text("\n".join(lineas) + ("\n" if lineas else ""), encoding="utf-8")
    return ruta


def verificar_manifiesto(raiz: Path) -> list[str]:
    """Compara el manifiesto con los archivos; devuelve las diferencias encontradas."""
    esperado = {}
    for linea in (raiz / MANIFIESTO).read_text(encoding="utf-8").splitlines():
        digest, _, nombre = linea.partition("  ")
        esperado[nombre] = digest
    errores = []
    actuales = {
        p.relative_to(raiz).as_posix(): p
        for p in raiz.rglob("*")
        if p.is_file() and p.name != MANIFIESTO
    }
    for nombre, digest in esperado.items():
        if nombre not in actuales:
            errores.append(f"falta {nombre}")
        elif hashlib.sha256(actuales[nombre].read_bytes()).hexdigest() != digest:
            errores.append(f"modificado {nombre}")
    errores += [f"no listado {n}" for n in sorted(set(actuales) - set(esperado))]
    return errores
