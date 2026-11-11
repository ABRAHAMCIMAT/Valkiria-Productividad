# 02 · Revisión de la arquitectura basada en Microsoft Azure

**Objetivo:** sustituir cada dependencia de Microsoft Azure (y de servicios propietarios en la nube) de la versión de referencia por la **mejor alternativa open source equivalente**. Las restricciones son:

- solo **mini LLMs gratuitos**
- ejecución local en **macOS y Windows**
- **32 GB de RAM como máximo** en una laptop
- backend en **Python** (última versión estable)
- frontend basado en **Jan**
- orquestación con lo mejor del ecosistema **LangChain**
- un framework **LLMOps** con trazabilidad y evidencias

Documentos relacionados: [01 · Ingeniería inversa](01-ingenieria-inversa.md) · [03 · Arquitectura de referencia](03-arquitectura-referencia.md) · [ADRs](adr/README.md)

---

## 1. Diagnóstico de la arquitectura actual

| # | Hallazgo en la versión de referencia | Riesgo | Severidad |
|---|---|---|---|
| D1 | Inferencia en Azure OpenAI (gpt-4o) | Los datos salen del equipo, costo por token, dependencia del proveedor, no funciona sin conexión | Alta |
| D2 | Embeddings en Azure (`text-embedding-ada-002`) además de embeddings locales | Dos índices incompatibles; costo; privacidad | Media |
| D3 | Backend propio en Azure App Service | Punto único de falla; requiere sesión corporativa para funcionar | Alta |
| D4 | Identidad con Entra ID (OAuth2/MSAL) obligatoria para los modelos del sistema | Sin cuenta no hay asistente | Alta |
| D5 | Integraciones exclusivas de Microsoft Graph (correo, calendario, Teams, OneNote, OneDrive, SharePoint) | Dependencia del proveedor; superficie de permisos amplia | Media |
| D6 | Actualizaciones publicadas desde un *gist* personal | Cadena de suministro frágil; sin trazabilidad de la publicación | Alta |
| D7 | Telemetría y observabilidad no auditables por el usuario | Falta de evidencia y de control | Media |
| D8 | Excepción ATS amplia (`NSExceptionAllowsInsecureHTTPLoads` con subdominios) | Permite HTTP en claro | Media |
| D9 | `shell_exec` con acceso completo al sistema de archivos | Ejecución arbitraria ante una inyección de prompt | Alta |
| D10 | Prompts incrustados en el binario (`include_str!`) | Cambiar un prompt obliga a recompilar; no hay versionado ni evaluación por versión | Media |
| D11 | Backend en Rust y helpers en Python (dos lenguajes, dos runtimes) | Mayor costo de mantenimiento | Baja |

## 2. Mapeo de Azure a open source

| Capacidad | Versión de referencia (Azure o propietario) | Sustituto open source elegido | Licencia | Alternativa para modo equipo o escala |
|---|---|---|---|---|
| Inferencia LLM | Azure OpenAI (gpt-4o) | **llama.cpp** (motor de Jan) + mini LLMs GGUF; **MLX** en Apple Silicon | MIT | vLLM o llama.cpp server en un servidor con GPU |
| Modelos de chat | gpt-4o | **Qwen3 4B/8B/14B**, Phi-4-mini, Granite, SmolLM3 ([ver §4](#4-catálogo-de-mini-llms-gratuitos)) | Apache 2.0 / MIT | Los mismos modelos con mayor cuantización |
| Embeddings | Azure `text-embedding-ada-002` | **multilingual-e5-small** / **bge-m3** (ONNX con fastembed) | MIT | Text Embeddings Inference (TEI) |
| Re-ranking | No existía | **bge-reranker-v2-m3** (ONNX) | Apache 2.0 | TEI |
| Búsqueda (AI Search) | SQLite FTS5 + sqlite-vec en Rust | **LanceDB** embebido (vector + FTS + híbrido) | Apache 2.0 | Qdrant / PostgreSQL + pgvector |
| Base de datos de la app | SQLite (sqlx) | **SQLite** con SQLAlchemy 2 + Alembic | Public domain / MIT | PostgreSQL |
| Backend (App Service) | Servicio .NET/Node en Azure | **Valkiria Core**: FastAPI + Uvicorn como *sidecar* local | MIT / BSD | Contenedor OCI en Kubernetes (k3s) |
| Orquestación del agente | ChatManagerV2 (Rust a medida) | **LangGraph** + **LangChain v1** (`create_agent`, middleware) | MIT | El mismo grafo servido por FastAPI |
| Herramientas | MCP interno (`rmcp`) | **MCP SDK de Python (FastMCP)** + `langchain-mcp-adapters` | MIT | Servidores MCP remotos sobre HTTP |
| Parsing de documentos (Document Intelligence) | pdfium, calamine y scripts Python | **Docling** + `pypdfium2` + RapidOCR | MIT / Apache 2.0 | Docling Serve |
| OCR y visión | Azure / gpt-4o vision | **Qwen3-VL 4B/8B** (GGUF) bajo demanda + RapidOCR | Apache 2.0 | vLLM con VLM |
| Voz (Speech) | Transcripción en la nube | **whisper.cpp** / faster-whisper (`large-v3-turbo`) | MIT | faster-whisper server |
| Identidad (Entra ID) | OAuth2 obligatorio | **Usuario local del sistema operativo** (sin cuenta) | — | **Keycloak** (OIDC) |
| Secretos (Key Vault) | Token cache propio | **Llavero del sistema operativo** (`keyring`: Keychain en macOS, Credential Manager en Windows) | MIT | **OpenBao** |
| Almacenamiento (Blob) | OneDrive / SharePoint | Sistema de archivos local cifrado por el SO (FileVault / BitLocker) | — | **SeaweedFS** o **Garage** (S3) |
| Correo, calendario, Teams (Graph) | Microsoft Graph | Conectores **MCP opcionales**: IMAP/SMTP, CalDAV/CardDAV, WebDAV (Nextcloud) | Varias OSS | El mismo conector en un servidor |
| Programador (Functions / Timer) | `cron` en Rust | **APScheduler 4** con almacén SQLite | MIT | APScheduler con PostgreSQL |
| Observabilidad (App Insights / Monitor) | Telemetría propietaria | **OpenTelemetry** + **MLflow Tracing** (local) | Apache 2.0 | Grafana + Tempo + Loki + Prometheus |
| LLMOps (Azure ML / Prompt Flow) | No existía | **MLflow 3** (tracking, tracing, Prompt Registry, evaluación, registro de modelos) | Apache 2.0 | MLflow server con PostgreSQL + S3, o **Langfuse** |
| Evaluación | No existía | `mlflow.genai.evaluate` + **Ragas** + **DeepEval** + pytest | Apache 2.0 / MIT | Lo mismo en CI |
| Red teaming | No existía | **promptfoo** (red team) + **garak** | MIT / Apache 2.0 | Lo mismo en CI |
| Guardrails (Content Safety) | No existía | **LLM Guard** + **Presidio** (PII) + **Qwen3Guard / Granite Guardian** opcional | MIT / Apache 2.0 | Lo mismo como servicio |
| Distribución y actualización | *Gist* + updater de Tauri | **GitHub Releases** + updater de Tauri (minisign) + atestaciones SLSA | — | Servidor de actualizaciones propio (estático) |
| CI/CD (Azure DevOps) | Desconocido | **GitHub Actions** (matriz macOS y Windows) | — | Gitea / Forgejo Actions |
| Seguridad de la cadena de suministro (Defender) | Desconocido | **Gitleaks**, **Semgrep**, **Bandit**, **pip-audit**, **Trivy**, **Syft** (SBOM CycloneDX), **OpenSSF Scorecard** | MIT / Apache 2.0 / LGPL (Semgrep CE) | Lo mismo |
| Interfaz de escritorio | Tauri 2 + SPA propia | **Fork de Jan** (Tauri + React) con marca Valkiria | Apache 2.0 | — |

> **Fuera de alcance:** la generación de imágenes y video (presente en la referencia mediante servicios en la nube). Puede añadirse después como un conector MCP opcional con modelos de difusión, pero viola el presupuesto de RAM si convive con el LLM.

## 3. Componentes del ecosistema LangChain: qué se adopta y qué no

| Componente | Decisión | Motivo |
|---|---|---|
| `langchain` v1: `create_agent` + **middleware** (Human-in-the-loop, Summarization, PII, límites de llamadas, Model fallback) | **Adoptar** | Cubre la confirmación, el resumen del historial y los límites de iteración que la referencia implementaba a mano |
| **LangGraph** (`StateGraph`, *checkpointer* SQLite, `interrupt`, subgrafos, `Store`) | **Adoptar** | Flujos deterministas con estado persistente; sub-agentes como subgrafos; reanudación tras la confirmación |
| `langchain-openai` (`ChatOpenAI` con `base_url` local) | **Adoptar** | Habla con el servidor compatible con OpenAI de llama.cpp/Jan sin acoplarse a él |
| `langchain-mcp-adapters` | **Adoptar** | Las herramientas MCP se vuelven herramientas de LangChain |
| `langchain-text-splitters`, *document loaders*, `langchain-docling` | **Adoptar** | Ingesta estándar |
| Integraciones de vector store / retrievers (LanceDB, `EnsembleRetriever`) | **Adoptar** | Búsqueda híbrida y re-ranking |
| **LangSmith** | **No adoptar** | SaaS propietario; se reemplaza por **MLflow 3** (que instrumenta LangChain/LangGraph con `autolog`) |
| LangGraph Platform / Server gestionado | **No adoptar** | Se sirve el grafo con FastAPI propio, de forma local |
| LangGraph Studio | **No adoptar** | Depende de la cuenta de LangSmith; la UI de trazas de MLflow cumple esa función |

## 4. Catálogo de mini LLMs gratuitos

Criterios para entrar al catálogo:

1. Licencia **Apache 2.0 o MIT** (o una licencia gratuita revisada que permita el uso previsto).
2. **14 B parámetros como máximo**.
3. Formato GGUF o MLX con **hash SHA-256 verificado**.
4. Pasar el gate de evaluación de la fase F1 ([plan](06-plan-desarrollo-incremental.md)).

| Rol | Modelo | Parámetros | Cuantización | RAM aprox. (pesos) | Licencia | Perfil |
|---|---|---|---|---|---|---|
| Principal (16 GB) | Qwen3-4B (instruct) | 4 B | Q4_K_M | 2.5 GB | Apache 2.0 | Estándar |
| Principal (32 GB) | Qwen3-8B | 8 B | Q4_K_M | 5.0 GB | Apache 2.0 | Avanzado |
| Techo de calidad (32 GB) | Qwen3-14B | 14 B | Q4_K_M | 9.0 GB | Apache 2.0 | Avanzado (bajo demanda) |
| Alternativa para benchmark | Phi-4-mini-instruct | 3.8 B | Q4_K_M | 2.4 GB | MIT | Ambos |
| Alternativa para benchmark | IBM Granite (3.3/4.x) 2B-8B | 2-8 B | Q4_K_M | 1.5-5 GB | Apache 2.0 | Ambos |
| Alternativa ligera | SmolLM3-3B | 3 B | Q4_K_M | 2.0 GB | Apache 2.0 | Estándar |
| Router, títulos, juez rápido | Qwen3-0.6B / 1.7B | 0.6-1.7 B | Q8_0 / Q4_K_M | 0.6-1.3 GB | Apache 2.0 | Ambos |
| Visión / OCR | Qwen3-VL-4B / 8B | 4-8 B | Q4_K_M + mmproj | 3.5-6 GB | Apache 2.0 | Bajo demanda |
| Guardrail | Qwen3Guard / Granite Guardian (pequeños) | 0.6-2 B | Q8_0 | 0.7-2 GB | Apache 2.0 | Opcional |
| Embeddings | multilingual-e5-small / bge-m3 | 0.1 / 0.6 B | ONNX int8 | 0.2 / 0.6 GB | MIT | Ambos |
| Re-ranker | bge-reranker-v2-m3 | 0.6 B | ONNX int8 | 0.6 GB | Apache 2.0 | Avanzado |
| Voz | whisper `small` / `large-v3-turbo` | 0.2 / 0.8 B | GGML | 0.5 / 1.6 GB | MIT | Bajo demanda |

> Los modelos con licencias con restricciones (por ejemplo, Llama Community o Gemma Terms) **no son la opción por defecto**. Solo se admiten tras una revisión legal registrada en un ADR. Las familias evolucionan rápido: el catálogo se revisa en cada cierre de fase y la elección final la decide la evaluación, no este documento.

## 5. Presupuesto de memoria (máximo 32 GB)

Política: **un solo modelo generativo grande cargado a la vez**, los modelos auxiliares pequeños se quedan residentes y los modelos de visión o voz se cargan bajo demanda y desplazan al principal. Valkiria no debe pasar de **22 GB** en el perfil Avanzado ni de **9 GB** en el Estándar.

| Componente | Perfil Estándar (16 GB) | Perfil Avanzado (32 GB) |
|---|---|---|
| Reservado al SO y a las aplicaciones del usuario | 7 GB | 10 GB |
| Valkiria Desktop (fork de Jan, WebView) | 0.5 | 0.5 |
| Valkiria Core (Python, LangGraph, LanceDB) | 0.8 | 1.2 |
| MLflow local (UI bajo demanda) | 0.2 | 0.3 |
| Embeddings + re-ranker | 0.3 (e5-small) | 1.2 (bge-m3 + reranker) |
| Router (Qwen3-0.6B / 1.7B) | 0.6 | 1.3 |
| LLM principal (pesos) | 2.5 (Qwen3-4B) | 5.0 (Qwen3-8B) / 9.0 (14B) |
| KV cache (KV en q8) | 0.6 (8 K tokens) | 1.2 (16 K) / 2.0 (32 K) |
| **Total de Valkiria** | **≈ 5.5 GB** | **≈ 10.7 GB (8B) / ≈ 15.5 GB (14B)** |
| Pico con visión o voz (desplaza al principal) | +1.5 | +3 |

Objetivos de rendimiento (gate de F1):

| Métrica | Perfil Estándar | Perfil Avanzado |
|---|---|---|
| Primer token (TTFT) con un prompt de 2 K tokens | ≤ 2.0 s | ≤ 1.5 s |
| Velocidad de generación | ≥ 15 tok/s | ≥ 20 tok/s (8B) |

Hardware objetivo:
- **macOS:** Apple Silicon M1 o posterior (Metal o MLX).
- **Windows:** x64 con GPU que soporte CUDA o Vulkan; con solo CPU se usa el perfil Estándar.

## 6. Resultado de la revisión

1. Las **11 debilidades** (D1 a D11) quedan cubiertas:
   - D1 a D4: inferencia, embeddings, backend e identidad pasan a local.
   - D5: los conectores se vuelven opcionales y abiertos.
   - D6: GitHub Releases con atestaciones.
   - D7: OpenTelemetry + MLflow, auditables por el usuario.
   - D8: solo `127.0.0.1` y TLS.
   - D9: sandbox y permisos de tres niveles.
   - D10: Prompt Registry versionado.
   - D11: un solo lenguaje en el backend (Python).
2. **Costo de operación por token: 0**, sin cuentas y sin conexión obligatoria.
3. Existe un **camino de escalamiento** (modo equipo) que reutiliza el mismo Valkiria Core en contenedores. Ver [03 · §9](03-arquitectura-referencia.md#9-escalabilidad-perfil-servidor-y-modo-equipo).
