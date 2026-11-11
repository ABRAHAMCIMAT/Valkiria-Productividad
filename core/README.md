# Valkiria Core

Backend local de Valkiria Productividad en **Python 3.15** ([ADR-0002](../docs/adr/ADR-0002-python-3-15.md)).
En F0 solo contiene el esqueleto del paquete, las herramientas de calidad y una verificación de salud;
el servicio FastAPI llega en F2.

```bash
cd core
uv sync --all-groups          # crea .venv con Python 3.15 y las herramientas de desarrollo
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest                 # falla si la cobertura baja de 85 %
```
