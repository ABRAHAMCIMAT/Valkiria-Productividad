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
2. **macOS x64 (Intel):** el frontend (Jan/Tauri) y el esqueleto de Core sí compilan, pero las capacidades de RAG (F3) y OCR (F8) **no tienen dependencias disponibles** para Intel. Se registró como riesgo **R-12**, con tres opciones: (a) soportar Intel con capacidades reducidas, (b) dejar de soportar Intel en 1.0 o (c) compilar las dependencias desde el código fuente (costo alto).

   **Decisión (2026-11-11): opción (b), con un mínimo más alto.** Valkiria para macOS requiere **Apple Silicon M4 o posterior con macOS 27.2 o superior**:
   - El instalador es solo `arm64` y el `.app` declara `LSMinimumSystemVersion` 27.2, así que macOS no lo abre en versiones anteriores.
   - El chip M4 es el hardware mínimo soportado y probado. No hay bloqueo técnico por chip: en M1, M2 o M3 con macOS 27.2 la app abre, pero sin soporte.
   - CI deja de usar `macos-15-intel`. Como los runners de GitHub no cumplen el mínimo, `desktop.yml` compila el `.app` y verifica su arquitectura y su `LSMinimumSystemVersion`, y la prueba de humo de macOS corre en un Mac M4 con `tools/desktop/humo-mac-local.sh`.
   - Se retiran las columnas de macOS x64 de la tabla anterior de las decisiones futuras.

## Revisión 2026-11-12 · R-11 (onnxruntime)

onnxruntime 1.31.1, su última versión, sigue sin *wheels* `cp315`. Se probó la alternativa que proponía este ADR en un Mac M4 con macOS 27.2 y Python 3.15:

| Paquete | Versión | *Wheel* para 3.15 |
|---|---|---|
| torch | 2.15.0 | `cp315` en macOS arm64 y Windows x64 |
| tokenizers, safetensors | 0.23.3, 0.8.0 | `abi3` |
| sentence-transformers, transformers | 6.3.0, 5.22.2 | Python puro |
| pyyaml | 6.0.3 | Sin *wheel* `cp315`: se instala desde el código fuente con su respaldo en Python puro, sin compilador |

`multilingual-e5-small` cargó sobre MPS y generó *embeddings* de 384 dimensiones; en una consulta de prueba, el pasaje relevante obtuvo una similitud de 0.896 y el irrelevante, de 0.749.

**Decisión: el *embedder* de F3 es `sentence-transformers` sobre torch, en lugar de fastembed sobre onnxruntime.** Los modelos del catálogo no cambian (e5-small y bge-m3, ADR-0011), ni se necesita la contingencia 3.14 para F3.

**Consecuencias:**
- R-11 queda **mitigado**. Solo depende de onnxruntime el respaldo de OCR de F8 (RapidOCR), ya que la vía principal es el VLM sobre llama.cpp. Se revisa al iniciar F8: si para entonces no hay *wheels* `cp315`, se usa solo el VLM o la contingencia 3.14 acotada a ese respaldo.
- torch pesa más que onnxruntime en el *sidecar* de PyInstaller (F2). Se mide el tamaño del instalador en F3 y, si hace falta, se usa la variante de torch solo CPU en Windows.
- EasyOCR no sirve como respaldo en 3.15: solo resuelve versiones antiguas, compiladas contra numpy 1.
- `spike-deps.yml` verifica cada semana la pila del *embedder* en Windows y macOS, exigiendo *wheels* para las dependencias nativas.
