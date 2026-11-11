"""CA-03.1, CA-03.2 y CA-03.3 con un MLflow real (SQLite temporal)."""

import json
from pathlib import Path
from typing import Any

from valkiria_llmops import demo, evidencia, experimentos

SHA = "0123456789abcdef0123456789abcdef01234567"


def test_experimentos_base_idempotentes(mlflow_local: tuple[Any, Any, str]) -> None:
    _, cliente, _ = mlflow_local
    primera = experimentos.asegurar(cliente)
    assert set(primera) == set(experimentos.EXPERIMENTOS)
    assert experimentos.asegurar(cliente) == primera


def test_ca_03_1_run_de_ejemplo_tiene_todos_los_tags(mlflow_local: tuple[Any, Any, str]) -> None:
    mlflow, cliente, _ = mlflow_local
    run_id = demo.ejecutar(mlflow, fase="F0", hu="HU-03", sha=SHA)
    run = cliente.get_run(run_id)
    assert run.data.tags["git.sha"] == SHA
    assert run.data.tags["gate.formato"] == "pass"
    assert run.data.metrics["json_valido"] == 1.0
    total, hallazgos = evidencia.gate(cliente, "F0")
    assert (total, hallazgos) == (1, [])


def test_ca_03_3_run_sin_git_sha_hace_fallar_el_gate(mlflow_local: tuple[Any, Any, str]) -> None:
    mlflow, cliente, _ = mlflow_local
    demo.ejecutar(mlflow, fase="F0", hu="HU-03", sha=SHA)
    mlflow.set_experiment("formato-eval")
    with mlflow.start_run(tags={"phase": "F0"}) as incompleto:
        pass
    total, hallazgos = evidencia.gate(cliente, "F0")
    assert total == 2
    mensajes = [str(h) for h in hallazgos]
    assert f"run {incompleto.info.run_id} (formato-eval): falta el tag git.sha" in mensajes
    assert all(h.run_id == incompleto.info.run_id for h in hallazgos)


def test_ca_03_2_exportacion_por_fase(mlflow_local: tuple[Any, Any, str], tmp_path: Path) -> None:
    mlflow, cliente, _ = mlflow_local
    ids = {demo.ejecutar(mlflow, fase="F0", hu="HU-03", sha=SHA) for _ in range(2)}
    demo.ejecutar(mlflow, fase="F1", hu="HU-04", sha=SHA)  # otra fase: no se exporta
    destino = tmp_path / "evidencias" / "F0"

    escritos = evidencia.exportar(cliente, "F0", destino)

    assert {p.stem for p in escritos} == ids
    doc = json.loads(escritos[0].read_text(encoding="utf-8"))
    assert doc["tags"]["phase"] == "F0"
    assert doc["metricas"]["json_valido"] == 1.0
    manifiesto = (destino / evidencia.MANIFIESTO).read_text(encoding="utf-8")
    assert all(f"mlflow/{i}.json" in manifiesto for i in ids)
    assert evidencia.verificar_manifiesto(destino) == []


def test_manifiesto_detecta_alteraciones(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("uno")
    (tmp_path / "b.txt").write_text("dos")
    evidencia.manifiesto(tmp_path)
    (tmp_path / "a.txt").write_text("alterado")
    (tmp_path / "b.txt").unlink()
    (tmp_path / "c.txt").write_text("nuevo")
    assert evidencia.verificar_manifiesto(tmp_path) == [
        "modificado a.txt",
        "falta b.txt",
        "no listado c.txt",
    ]


def test_manifiesto_vacio(tmp_path: Path) -> None:
    assert evidencia.manifiesto(tmp_path).read_text() == ""


def test_evaluar_detecta_json_invalido() -> None:
    assert demo.evaluar([{"salida": "{}"}, {"salida": "no es json"}])["json_valido"] == 0.5
    assert demo.evaluar([])["json_valido"] == 0.0
