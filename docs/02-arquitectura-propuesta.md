# 02 · Arquitectura propuesta: Valkiria Productividad (local)

Asistente de escritorio de **VALTRE** que corre por completo en el equipo del usuario, con modelos LLM pequeños de código abierto. No requiere cuenta, no necesita internet para funcionar y los datos no salen del equipo.

## 1. Principios

1. **Local primero.** Inferencia, embeddings, índice y archivos se quedan en el equipo. Internet solo para descargar modelos y, si el usuario lo activa, para búsqueda web.
2. **Diseñado para modelos pequeños** (de 0.6 a 8 B parámetros): prompts cortos, pocas herramientas por turno, salida estructurada y el backend hace el trabajo pesado.
3. **Proveedor intercambiable:** un *trait* `LlmProvider` permite cambiar entre Ollama, llama.cpp, MLX o cualquier API compatible con OpenAI.
4. **Medible:** una suite de evaluación (`evals/`) se ejecuta en cada cambio de modelo o de prompt.

## 2. Diagrama

```
┌──────────────────────────── Valkiria Productividad (Tauri 2) ────────────────────────────┐
│ UI React + TypeScript                                                                    │
│  Chat · Mis archivos · Proyectos · Programador · Skills · Configuración · Cmd+K          │
│        │ invoke / events (streaming de tokens)                                           │
│ Backend Rust (tokio)                                                                     │
│  ├─ Orchestrator: router de intención → ensamblado de prompt → bucle de herramientas     │
│  ├─ LlmProvider ──► Ollama :11434 │ llama-server :8080 │ MLX │ API compatible con OpenAI │
│  ├─ Tools: archivos, RAG, Office (Python/uv), shell (con permisos), scheduler            │
│  ├─ RAG: extractores → chunker → fastembed (e5-small) → SQLite FTS5 + sqlite-vec         │
│  ├─ Skills loader (SKILL.md)   ├─ Cliente MCP (rmcp)   ├─ Scheduler (cron)               │
│  └─ Voz: whisper.cpp          └─ Visión: VLM local para OCR y descripción de imágenes    │
│ Datos: ~/Library/Application Support/valkiria/ (valkiria.db, config.json, models/, ...)  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## 3. Stack

| Componente | Elección | Justificación |
|---|---|---|
| Shell | Tauri 2 | Ligero, seguro, multiplataforma; es la arquitectura que ya está probada en la referencia |
| UI | React + TypeScript + Vite, Tailwind, `react-markdown` + KaTeX | Ecosistema maduro |
| Backend | Rust (tokio, sqlx, reqwest) | Rendimiento y un solo binario |
| Motor LLM | **Ollama** (fase 0), con llama.cpp `llama-server` y MLX como alternativas | API compatible con OpenAI y *structured outputs* (JSON schema) |
| Embeddings | `multilingual-e5-small` con fastembed-rs (384 dimensiones), con `bge-m3` como opción de mayor calidad | Multilingüe y ligero |
| Base de datos | SQLite (WAL) + FTS5 + sqlite-vec | Búsqueda híbrida en un solo archivo |
| Office/PDF | Python gestionado con `uv` + helpers JSON por stdin | openpyxl, python-docx, python-pptx, pdfplumber |
| Voz | whisper.cpp (`small` o `large-v3-turbo`) | Transcripción sin conexión |
| Extensiones | MCP (`rmcp`) | Integraciones externas sin recompilar |

## 4. Modelos recomendados

Equipo de referencia: Apple M4 con 16 GB de RAM.

| Rol | Modelo (cuantización Q4_K_M) | RAM aprox. | Uso |
|---|---|---|---|
| Principal | Qwen3 4B o Qwen3 8B | 3 a 5.5 GB | Chat, RAG, uso de herramientas |
| Router y utilidades | Qwen3 0.6B o 1.7B | 0.5 a 1.5 GB | Clasificar la intención, generar títulos, resúmenes cortos |
| Visión | Gemma 3 4B o Qwen2.5-VL 3B | 3 a 4 GB | OCR, descripción de imágenes y PDFs escaneados |
| Alternativas para benchmark | Phi-4-mini, Llama 3.2 3B, SmolLM3 3B | 2 a 3 GB | Comparar en la suite de evaluación |
| Embeddings | multilingual-e5-small | ~0.5 GB | Búsqueda semántica |
| Voz | whisper `small` o `large-v3-turbo` | 0.5 a 1.6 GB | Dictado |

Regla práctica: mantener cargado **un** modelo grande a la vez (con `keep_alive` de Ollama) y descargarlo cuando entre la visión.

## 5. Adaptaciones para modelos pequeños

| Problema | Solución |
|---|---|
| Contexto corto (8 a 16 K tokens) | Prompt de sistema de menos de 2 K tokens; resumen automático del historial; RAG con top-k de 4 a 6 fragmentos |
| Uso de herramientas poco fiable | Salida restringida por JSON schema o gramática GBNF; un máximo de 5 a 8 herramientas por turno; descripciones cortas con un ejemplo |
| Elección de herramienta | **Router**: el modelo pequeño clasifica la intención (`chat`, `rag`, `files`, `office`, `schedule`) y solo se cargan esas herramientas |
| Alucinación de citas | El backend numera las fuentes y valida que cada `[N]` exista; si no existe, se elimina |
| Búsqueda iniciada por el modelo | **RAG inyectado**: el backend recupera antes de llamar al LLM cuando la intención es `rag` |
| Bucles infinitos | Límite de iteraciones (por ejemplo, 6), presupuesto de tiempo, detección de llamadas repetidas |
| Documentos largos | Map-reduce por tramos (equivalente a los sub-agentes de solo lectura) |

## 6. Modelo de datos inicial

```sql
threads(id, title, project_id, folder_id, pinned, source, created_at, updated_at)
messages(id, thread_id, role, content, metadata_json, created_at)
projects(id, name, personality, created_at, updated_at)
project_skills(project_id, skill_name)
files(id, path UNIQUE, name, ext, mime, size, hash, modified_at, project_id,
      text_excerpt, needs_embedding, embedding_error)
chunks(id, source_type, content_id, chunk_index, text, page, section,
       start_token, end_token, project_id)
chunks_fts USING fts5(text, section, tokenize='porter unicode61 remove_diacritics 2')
chunks_vec USING vec0(chunk_id INTEGER PRIMARY KEY, embedding float[384], source_type TEXT)
scheduled_tasks(id, name, enabled, cron, tz, prompt, thread_id, next_run, last_run,
                last_status, consecutive_errors)
mcp_servers(id, name, type, enabled, config_json)
permissions(capability PRIMARY KEY, level CHECK(level IN ('block','ask','allow')))
```

## 7. Interfaces clave (Rust)

```rust
#[async_trait]
pub trait LlmProvider: Send + Sync {
    async fn list_models(&self) -> Result<Vec<ModelInfo>>;
    async fn chat_stream(&self, req: ChatRequest) -> Result<BoxStream<'static, Result<ChatDelta>>>;
    fn capabilities(&self, model: &str) -> ModelCaps; // tools, vision, json_schema, ctx_len
}

pub trait Tool: Send + Sync {
    fn name(&self) -> &'static str;
    fn schema(&self) -> serde_json::Value;          // JSON schema de los argumentos
    fn capability(&self) -> Capability;             // para los permisos
    async fn call(&self, args: serde_json::Value, ctx: &ToolCtx) -> Result<ToolResult>;
}
```

## 8. Seguridad y privacidad

- Permisos de tres niveles (bloquear, preguntar o permitir) por capacidad: lectura de archivos, escritura, shell y red.
- `shell_exec` desactivado por defecto; cuando se activa, siempre muestra una tarjeta de confirmación.
- Lista de rutas permitidas para leer y escribir; espacio de trabajo temporal por conversación.
- Sin telemetría por defecto.
- Actualizaciones firmadas (minisign) con el plugin updater de Tauri.
