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
