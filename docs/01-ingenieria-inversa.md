# 01 · Ingeniería inversa de la versión de referencia

Este documento describe cómo está construida la versión de referencia de **Valkiria Productividad Desktop (v1.4.1, macOS arm64)**, un asistente de IA de escritorio que trabaja con modelos en la nube. El objetivo es extraer la arquitectura y los patrones que vale la pena conservar en la nueva solución local de **VALTRE**.

> **Método.** Análisis estático del paquete `.app`: `Info.plist`, recursos incluidos, cadenas del binario (lista de crates de Rust, endpoints, nombres de tipos) y **estructura** de la base de datos local y del archivo de configuración (solo nombres de tablas y claves, sin leer datos de usuario).

---

## 1. Vista general

```
┌──────────────────── Valkiria Productividad.app (Tauri 2, arm64, ~47 MB) ────────────────────┐
│  Frontend (WebView / WKWebView)             Backend Rust (tokio)                             │
│  SPA construida con Vite         ◄── IPC ──► ChatManagerV2 (bucle agéntico)                  │
│  (index-*.js, KaTeX,                         ├─ prompt.rs: ensamblado del system prompt      │
│   docx-preview, widgets)                     ├─ Proveedores LLM (API compatible con OpenAI)  │
│                                              ├─ Servidores MCP internos (rmcp 0.13)          │
│                                              ├─ Sub-agentes delegate_* (solo lectura)        │
│                                              ├─ RAG: fastembed + ort (ONNX) local            │
│                                              ├─ SQLite (sqlx) + FTS5 + sqlite-vec            │
│                                              ├─ Programador (cron) + notificaciones          │
│                                              └─ OAuth2 → Microsoft Graph                     │
│  Resources/: prompts/, skills/, specialists/, quick_actions/, python-runtime/ (uv)           │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
        │ LLM en la nube: Azure OpenAI (gpt-4o, text-embedding-ada-002) + backend propio en Azure
        │ Proveedores alternos presentes en el código: Ollama :11434, LM Studio :1234,
        │ vLLM :8000, OpenAI, Anthropic
```

## 2. Stack tecnológico

| Capa | Hallazgo |
|---|---|
| Shell de escritorio | **Tauri 2.11** (tao + wry). Plugins: `fs`, `shell`, `dialog`, `notification`, `updater` (firmas minisign), `single-instance`, `clipboard-manager`, `opener`, `os`; ícono en bandeja (`tray-icon`) y menús (`muda`). |
| Frontend | SPA construida con Vite (assets con hash). Usa KaTeX (fórmulas), `docx-preview` y changelogs por versión cargados de forma diferida. El framework no se pudo confirmar porque los assets van comprimidos dentro del binario (probablemente React). |
| Runtime | `tokio`, `reqwest`, `hyper`, `rustls`, `sse-stream` (streaming de respuestas). |
| LLM | Cliente de `chat/completions` (formato OpenAI y Azure con `api-version`) y tipos nativos de la API de Anthropic. Catálogo de "modelos del sistema" servido por el backend y "modelos personalizados" que agrega el usuario (OpenAI, Azure OpenAI, Anthropic, LM Studio). |
| Conteo de tokens | `tiktoken-rs`, `tokenizers` (Hugging Face). |
| Embeddings locales | `fastembed 5.8` + `ort 2.0` (ONNX Runtime). Modelo descargado: **`intfloat/multilingual-e5-small`** (384 dimensiones). El código también soporta bge-small/base/large, bge-m3, all-MiniLM-L6/L12 y multilingual-e5-base/large. |
| Visión local | `mobilenet_v3_small.onnx` (clasificación de imágenes para la búsqueda avanzada). |
| Documentos (Rust) | `pdfium-render` (con `libpdfium.dylib` descargada), `lopdf`, `pdf-extract`, `calamine` (Excel), `html2text`, `scraper`, `pulldown-cmark`, `zip`, `quick-xml`. |
| Documentos (Python) | Python 3.12 gestionado con **`uv`**: openpyxl, python-docx, python-pptx, pypdf, pdfplumber, pypdfium2, reportlab, pandas, numpy, matplotlib, seaborn. |
| Persistencia | `sqlx` + SQLite (modo WAL), FTS5 y la extensión **sqlite-vec** (`vec0`). |
| Sistema de archivos | `notify` (FSEvents), `ignore`, `globset`, `walkdir`. |
| Programador | `cron 0.15`, `chrono-tz` (zona horaria por defecto `America/Mexico_City`). |
| Integraciones | `oauth2` + callback local `http://localhost:9898/auth/callback`; Microsoft Graph (`v1.0` y `beta`): correo, calendario, Teams, OneNote, OneDrive, SharePoint. |
| Web | Búsqueda en DuckDuckGo HTML o Brave Search API. |
| Extensibilidad | `rmcp` (Model Context Protocol), servidores MCP de tipo `local`, `docker` o `remote`; viene un ejemplo con el servidor MCP de GitHub. |

## 3. Datos locales

Directorio de datos de la app (`~/Library/Application Support/<app>/`, unos 1.2 GB):

```
app.db (+ -wal, -shm)      Base de datos SQLite principal
config.json                Configuración del usuario
workspace/<thread_id>/     Espacio de trabajo temporal por conversación
models/                    Modelos ONNX auxiliares
fastembed_cache/           Modelo de embeddings (multilingual-e5-small)
libs/libpdfium.dylib       Motor de PDF
python-runtime/            CPython 3.12 + venv + scripts
chat_paste_cache/          Contenido pegado en el chat
logs/
```

### 3.1 Esquema de la base de datos

| Dominio | Tablas |
|---|---|
| Conversaciones | `chat_threads` (title, rag_context, source `user`/`scheduled`, `scheduled_task_id`, `project_id`, `folder_id`, `pinned`), `chat_messages` (role, content, metadata JSON), `state_snapshots`, `chat_folders` |
| Proyectos | `projects` (name, personality, cuota de almacenamiento de 200 MB, origin `local`/remoto, remote_author), `project_skills`, `project_specialists` |
| Archivos locales | `files` (path, ext, mime, hash, text_excerpt, excerpt_method, has_embeddings, needs_embedding, embedding_error, sync_state, project_id), `files_fts` |
| RAG unificado | `unified_embeddings` (content_id, source_type, chunk_index, chunk_text, start_token, end_token, section_title, page_number, vector BLOB, project_id), `unified_chunks_fts`, `unified_vec_embeddings` (`vec0`, `float[384]`, columna de metadatos `source_type`) |
| Nube | `onedrive_files`, `onenote_notebooks`, `onenote_sections`, `onenote_pages` (+ `onenote_pages_fts`), `graph_cache` (caché con TTL por namespace), `user_photos` |
| Sincronización | `sync_metadata` (email, calendar, teams, onedrive), `sync_history` (contadores creados/actualizados/eliminados/fallidos, duración, estado) |
| Programador | `scheduled_tasks` (schedule_expr cron, schedule_tz, prompt, thread_id, generation_config, next_run, last_status, consecutive_errors, context_mode `continuous`), `scheduler_state` |
| Extensiones | `mcp_servers` (server_type, enabled, is_system, chat_contexts, config_json) |

Todas las tablas FTS usan `tokenize='porter unicode61 remove_diacritics 2'`, de modo que la búsqueda ignora acentos.

### 3.2 Configuración (`config.json`)

Bloques principales: `folders` / `individual_files` (qué indexar), `appearance`, `privacy.telemetry_enabled`, `rag` (`enabled`, `hybrid_search`, `max_results`, `embedding_timeout_secs`, `advanced_image_search`, `image_captioning_provider`), `advanced.system_prompt` (prompt personalizado), `advanced.mcp_tools.*` (activación de cada servidor MCP según el contexto), `advanced.api_endpoints` (Azure, Hugging Face, repositorio de fastembed), `ai_models` (modelos del sistema, modelos personalizados, selección activa), `integrations.*` (intervalos de sincronización y carpetas o cuadernos elegidos), `ignored_extensions`, `max_file_size_mb`, `auto_indexing_enabled`.

## 4. Sistema agéntico

Es la parte de mayor valor para el diseño de la nueva solución.

### 4.1 Prompt de sistema modular

Los prompts viven en archivos `.txt` que se incrustan en el binario (`include_str!`). El orden de ensamblado es:

1. Rol base (o el override del usuario)
2. Fecha y hora actuales (día de la semana, hora local, desfase UTC)
3. `rules_core.txt`: reglas fundamentales
4. `behavior_proactive.txt`: actuar sin preguntar (solo en los contextos Main y Files)
5. `tools/files.txt`: herramientas de archivos
6. `tools/<integración>.txt`: solo las integraciones habilitadas (`EnabledFeatures { calendar, email, teams, onenote, orgnav }`)
7. `citations.txt`: instrucciones de citas para RAG
8. `contexts/<contexto>.txt`: Main, Files, Calendar o Simple
9. Instrucciones que aporta cada servidor MCP

Hay además bloques transversales: `planning.txt`, `rendering.txt`, `output_efficiency.txt`, `error_recovery.txt`, `confirmation_banner.txt`, `restrictions_banner.txt` y `blocked_tool_reason.txt`.

| Contexto | Herramientas de archivos | Integraciones | Citas | Proactivo |
|---|---|---|---|---|
| Main | Sí | Sí (según features) | Sí | Sí |
| Files | Sí | No | No | Sí |
| Calendar | No | No | No | No |
| Simple | No | No | No | No |

### 4.2 Catálogo diferido de herramientas

No se cargan todas las herramientas a la vez. El modelo ve un catálogo de categorías y carga las que necesita con `search_tools({"query": "..."})`. Esto mantiene corto el contexto, y será **imprescindible** con modelos pequeños.

Algunas de las herramientas identificadas:

- **Archivos:** `search_files`, `read_file`, `grep_files`, `fs_list_dir`, `fs_stat`, `fs_write_file`, `fs_edit_file`, `shell_exec`
- **Office/PDF:** `xlsx_read`, `docx_read`, `pptx_read`, `pdf_read`, `pdf_ocr`, `pdf_create`, `save_as`
- **Integraciones:** `search_emails`, `create_draft`, `search_calendar`, `create_event`, `update_event`, `search_messages`, `search_notes`, `search_cloud_files`
- **Agente:** `update_todos`, `load_skill`, `search_tools`, `generate_widget`, `delegate_*`
- **Programador:** `scheduler_list`, `scheduler_update`, `scheduler_delete`, `scheduler_set_enabled`
- **Generación:** imágenes y video

### 4.3 Skills

Cada skill es una carpeta con un `SKILL.md`:

```markdown
---
name: xlsx
description: Crear y editar hojas de cálculo Excel con Python (openpyxl)...
allowed-tools: shell_exec read_file fs_write_file
---
Instrucciones + API del helper...
```

y `scripts/*.py`: helpers que reciben JSON por stdin y devuelven JSON (`create`, `read`, `edit`, `find`), con pruebas unitarias. Se cargan bajo demanda con `load_skill`, que además devuelve la ruta `dir` de la skill.

Skills incluidas: `docx`, `xlsx`, `pptx`, `pdf-tools`, `html`, `calendar`, `email`, `teams`, `create-skill` (para que el usuario cree las suyas) y una guía de la propia app.

### 4.4 Sub-agentes especialistas

Son `delegate_general`, `delegate_researcher`, `delegate_analyst`, `delegate_meetings` y `delegate_teams`, definidos en `specialists/*.md`. Sus reglas:

- **Solo leen y resumen**, nunca ejecutan acciones de escritura. El agente principal hace la recolección por medio del sub-agente y luego ejecuta la acción él mismo.
- Se delega solo si la tarea requiere 3 o más lecturas, paginar fuentes largas (transcripciones, historiales) o leer documentos largos **por tramos** (por ejemplo, 40 páginas o 20 páginas escaneadas por tramo).
- Cada sub-agente tiene su propia ventana de contexto y un **presupuesto de tiempo e iteraciones**. Si se agota, devuelve `[partial: sub-agent reached its time budget]` con una línea de cobertura, y el agente principal decide si vuelve a delegar el tramo faltante.
- Las citas `[N]` de los sub-agentes se integran automáticamente en la respuesta final.

### 4.5 Permisos y confirmación

- Cada capacidad tiene uno de tres niveles: **Bloquear**, **Pedir confirmación** o **Permitir sin preguntar**, configurables por integración.
- Cuando hay que confirmar, la UI muestra una **tarjeta interactiva** con los argumentos. El modelo solo anuncia la acción en una frase y no pide confirmación por texto.
- Si el usuario rechaza o se agota el tiempo, el modelo lo trata como un "no" y no reintenta con variaciones.
- `fs_edit_file` exige haber leído antes el fragmento que se va a modificar y devuelve un diff.

### 4.6 Otros patrones

- **Plan visible (`update_todos`):** solo para tareas de varias etapas; de 3 a 7 pasos, con un único paso `in_progress`.
- **Widgets declarativos:** el modelo no escribe código, sino una especificación con `inputs`, `derived`, `state` (recurrencias paso a paso) y `outputs`/`chart`, que la UI renderiza.
- **Citas:** el modelo marca `[N]` y un `CitationTracker` en el backend extrae los `file_id` de las llamadas a herramientas.
- **Acciones rápidas:** archivos `quick_actions/*.md` con frontmatter (`title`, `label`, `icon`, `argument-hint`) y la plantilla `$ARGUMENTS`.
- **Proyectos:** personalidad, banco de archivos (RAG filtrado por `project_id`), skills y especialistas propios; se pueden compartir como copia.
- **Store:** catálogo comunitario de skills y proyectos compartidos.
- **Programador:** tareas cron con prompt, hilo propio, `context_mode` y conteo de errores consecutivos; notifican al sistema al terminar.
- **UX:** paleta de comandos (Cmd/Ctrl+K), contexto fijado (eventos, correos o archivos anclados al chat), notificaciones, tema claro/oscuro, actualizaciones automáticas firmadas.

## 5. Pipeline de RAG observado

```
Carpeta vigilada (notify)
  → extracción de texto (pdfium / calamine / docx / html2text) → files.text_excerpt
  → chunking por tokens (start_token / end_token, section_title, page_number)
  → embedding local multilingual-e5-small (ONNX, 384 dimensiones)
  → unified_embeddings + unified_vec_embeddings (vec0) + unified_chunks_fts (FTS5)
Consulta
  → búsqueda híbrida (BM25 de FTS5 + KNN de vec0) → top-k → contexto con citas [N]
```

Las fuentes (`source_type`) comparten el mismo índice: archivos locales, OneDrive, OneNote y archivos de proyecto.

## 6. Conclusiones para la nueva solución

**Conservar:**
- Tauri 2 con backend en Rust
- SQLite con FTS5 y sqlite-vec y el esquema `unified_*`
- fastembed con e5-small
- Prompt modular y catálogo diferido de herramientas
- Skills con `SKILL.md` y helpers Python ejecutados con `uv`
- Permisos de tres niveles con tarjeta de confirmación
- Sub-agentes de solo lectura con presupuesto
- Programador cron
- Proyectos

**Cambiar:**
- El LLM en la nube por **modelos pequeños open source locales**. Eso obliga a usar prompts mucho más cortos (los de la referencia suman unos 200 KB), pocas herramientas por turno, salida JSON restringida y RAG inyectado.
- Las integraciones con Microsoft 365 pasan a ser opcionales (como servidores MCP), para que la base sea 100 % local y sin cuentas.

**Aviso:** los prompts, skills y scripts de la versión de referencia pertenecen a su titular. Se usan solo como referencia de arquitectura; la nueva solución debe escribir su propio código y sus propios prompts.
