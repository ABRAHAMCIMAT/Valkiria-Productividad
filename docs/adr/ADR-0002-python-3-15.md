# ADR-0002 · Backend en Python 3.15

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Contexto
Requisito: todo el backend se escribe en Python, en su **última versión estable**. Python **3.15.0** se publicó el 9 de octubre de 2026 e incluye UTF-8 por defecto, `lazy import`, `frozendict`, ABI estable para *free-threaded* y *frame pointers* activos (útiles para la observabilidad).

## Decisión
- `requires-python = ">=3.15,<3.16"` y gestión con **uv** (`uv.lock` con hashes); el intérprete se fija con `uv python pin 3.15`.
- Herramientas: `ruff`, `mypy --strict`, `pytest`, `pydantic` v2, `SQLAlchemy` 2 y `FastAPI`.
- Se usa el *build* estándar con GIL. El *free-threaded* se evalúa en F11, pensando en el servidor.

## Consecuencias y contingencia
- Riesgo **R-01**: algunas *wheels* nativas (onnxruntime, lancedb, docling, pyinstaller) pueden tardar en publicar versiones para 3.15 en Windows o macOS x64.
- *Spike* en F0: `uv sync` en la matriz completa de CI.
- Si una dependencia crítica no está disponible, se permite **de forma temporal** un *build* 3.14 **solo para esa plataforma**, registrado como riesgo con fecha de vencimiento (la próxima versión menor de la dependencia). CI ejecuta las pruebas en ambas versiones durante la contingencia.

## Resultado del spike de F0 (2026-11-10)
Consulta a PyPI de las últimas versiones; la verificación real con instalación (`--only-binary :all:`) la repite cada semana el workflow [`spike-deps.yml`](../../.github/workflows/spike-deps.yml) en `macos-15`, `macos-15-intel` y `windows-2022`, con Python 3.15 y 3.14.

| Dependencia | Fase | macOS arm64 · 3.15 | macOS x64 · 3.15 | Windows x64 · 3.15 | Nota |
|---|---|---|---|---|---|
| pyinstaller 6.22 | F2 | ✔ | ✔ | ✔ | *wheel* `py3-none` por plataforma |
| numpy, pyarrow, tokenizers, pydantic-core, watchfiles, spacy | F2–F5 | ✔ | ✔ | ✔ | |
| lancedb 0.41 (abi3) | F3 | ✔ | ✗ | ✔ | No publica *wheel* para macOS x64 en ninguna versión |
| torch 2.15 (docling) | F3 | ✔ | ✗ | ✔ | PyTorch dejó de publicar para macOS x64 |
| **onnxruntime 1.31** (fastembed, RapidOCR) | F3, F8 | ✗ | ✗ | ✗ | Sin *wheels* `cp315` en ninguna plataforma; tampoco hay macOS x64 en ninguna versión |
| Puros Python (fastapi, mlflow-skinny, langgraph, docling, fastembed, presidio) | — | ✔ | ✔ | ✔ | |

**Consecuencias para el plan:**
1. **onnxruntime:** se activa la contingencia descrita arriba en cuanto F3 lo necesite: *build* 3.14 para Core en macOS arm64 y Windows, registrado como riesgo **R-11** con vencimiento en la primera versión de onnxruntime con *wheels* `cp315`. Mientras tanto se evalúa un *embedder* sin onnxruntime (por ejemplo, `sentence-transformers` sobre torch) como alternativa.
2. **macOS x64 (Intel):** el frontend (Jan/Tauri) y el esqueleto de Core sí compilan, pero las capacidades de RAG (F3) y OCR (F8) **no tienen dependencias disponibles** para Intel. Se registra como riesgo **R-12** y requiere una decisión del Product Owner antes de F3: (a) soportar Intel con capacidades reducidas, (b) dejar de soportar Intel en 1.0 o (c) compilar las dependencias desde el código fuente (costo alto).
