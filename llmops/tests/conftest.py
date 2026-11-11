from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def mlflow_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, Any, str]]:
    """MLflow real con backend SQLite temporal: ``(mlflow, cliente, uri)``."""
    import mlflow

    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", uri)
    monkeypatch.chdir(tmp_path)  # los artefactos locales quedan dentro de tmp_path
    mlflow.set_tracking_uri(uri)
    yield mlflow, mlflow.MlflowClient(uri), uri
    mlflow.set_tracking_uri(None)
