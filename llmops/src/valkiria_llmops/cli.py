"""CLI ``llmops``: servidor local, experimentos base, ejemplo, gate y exportación."""

from __future__ import annotations

import argparse
import ipaddress
import os

# Solo lanza el servidor de MLflow con argumentos controlados.
import subprocess  # nosec B404
import sys
from collections.abc import Sequence
from pathlib import Path

HOST_POR_DEFECTO = "127.0.0.1"
PUERTO_POR_DEFECTO = 5000
URI_POR_DEFECTO = f"http://{HOST_POR_DEFECTO}:{PUERTO_POR_DEFECTO}"
RAIZ_REPO = Path(__file__).resolve().parents[3]


def directorio_datos() -> Path:
    return Path(os.environ.get("VALKIRIA_MLFLOW_HOME", Path.home() / ".valkiria" / "mlflow"))


def comando_servidor(host: str, puerto: int, datos: Path) -> list[str]:
    """Comando de ``mlflow server``. Rechaza cualquier host que no sea loopback (RN-03.3)."""
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    if not loopback:
        raise ValueError(f"MLflow solo puede escuchar en loopback (RN-03.3), no en {host!r}")
    return [
        sys.executable, "-m", "mlflow", "server",
        "--backend-store-uri", f"sqlite:///{(datos / 'mlflow.db').as_posix()}",
        "--artifacts-destination", (datos / "artifacts").as_uri(),
        "--host", host, "--port", str(puerto),
    ]  # fmt: skip


def _cliente(uri: str):  # type: ignore[no-untyped-def]
    import mlflow

    mlflow.set_tracking_uri(uri)
    return mlflow, mlflow.MlflowClient(uri)


def main(argv: Sequence[str] | None = None) -> int:
    os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
    ap = argparse.ArgumentParser(prog="llmops", description=__doc__)
    ap.add_argument(
        "--tracking-uri", default=os.environ.get("MLFLOW_TRACKING_URI", URI_POR_DEFECTO)
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="Levanta MLflow local (solo 127.0.0.1)")
    s.add_argument("--host", default=HOST_POR_DEFECTO)
    s.add_argument("--port", type=int, default=PUERTO_POR_DEFECTO)
    s.add_argument("--dry-run", action="store_true", help="Solo imprime el comando")

    sub.add_parser("bootstrap", help="Crea los experimentos base (idempotente)")

    d = sub.add_parser("demo-eval", help="Run de ejemplo etiquetado (formato JSON)")
    d.add_argument("--phase", required=True)
    d.add_argument("--hu", required=True)

    g = sub.add_parser("gate", help="Valida los tags obligatorios de los runs de una fase")
    g.add_argument("--phase", required=True)

    e = sub.add_parser("export", help="Exporta los runs de una fase a evidencias/<fase>/")
    e.add_argument("--phase", required=True)
    e.add_argument("--out", type=Path)

    a = ap.parse_args(argv)

    if a.cmd == "serve":
        datos = directorio_datos()
        try:
            cmd = comando_servidor(a.host, a.port, datos)
        except ValueError as err:
            print(f"error: {err}", file=sys.stderr)
            return 2
        print(" ".join(cmd))
        if a.dry_run:
            return 0
        (datos / "artifacts").mkdir(parents=True, exist_ok=True)  # pragma: no cover
        return subprocess.call(cmd)  # noqa: S603  # pragma: no cover  # nosec B603

    from valkiria_llmops import demo, evidencia, experimentos

    mlflow, cliente = _cliente(a.tracking_uri)
    if a.cmd == "bootstrap":
        for nombre, exp_id in experimentos.asegurar(cliente).items():
            print(f"{nombre}: {exp_id}")
        return 0
    if a.cmd == "demo-eval":
        experimentos.asegurar(cliente)
        print(demo.ejecutar(mlflow, fase=a.phase, hu=a.hu))
        return 0
    if a.cmd == "gate":
        total, hallazgos = evidencia.gate(cliente, a.phase)
        for h in hallazgos:
            print(f"::error title=Gate {a.phase}::{h}")
        if total == 0:
            print(f"::error title=Gate {a.phase}::no hay runs con phase={a.phase}")
            return 1
        print(f"{total} runs revisados, {len(hallazgos)} hallazgos")
        return 1 if hallazgos else 0
    destino = a.out or RAIZ_REPO / "evidencias" / a.phase
    escritos = evidencia.exportar(cliente, a.phase, destino)
    print(f"{len(escritos)} runs exportados a {destino}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
