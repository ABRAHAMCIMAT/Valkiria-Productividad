# 03 · Plan de desarrollo incremental

Cada fase deja una aplicación funcional y tiene un criterio de "terminado" verificable. Las duraciones son estimadas para una persona.

## Resumen

| Fase | Nombre | Duración | Entregable principal |
|---|---|---|---|
| 0 | Base | 1 semana | Chat local con streaming |
| 1 | Persistencia | 1 semana | Historial de conversaciones |
| 2 | RAG local | 2 semanas | Preguntas sobre mis archivos con citas |
| 3 | Herramientas | 2 semanas | Bucle agéntico con permisos |
| 4 | Router y prompt modular | 1 semana | Prompt corto y herramientas por intención |
| 5 | Skills y Office | 2 semanas | Crear docx, xlsx y pptx |
| 6 | Proyectos | 1 semana | Espacios con personalidad y archivos propios |
| 7 | Multimodal y voz | 2 semanas | OCR, imágenes y dictado |
| 8 | Automatización | 1 semana | Tareas programadas |
| 9 | Avanzado | Continuo | Map-reduce de documentos, MCP, widgets, empaquetado |

---

## Fase 0 · Base

- Proyecto Tauri 2 + React + TypeScript (`npm create tauri-app`).
- Trait `LlmProvider` con su implementación para Ollama (`/api/tags`, `/v1/chat/completions` con streaming SSE).
- Pantalla de chat mínima: entrada, streaming de tokens, botón para detener.
- Comprobar al iniciar que Ollama está disponible y que el modelo está descargado (si no, mostrar cómo hacer `ollama pull`).

**Terminado cuando:** se puede conversar con Qwen3 4B sin internet y el primer token llega en menos de 1 s.

## Fase 1 · Persistencia

- SQLite con sqlx y migraciones: `threads` y `messages`.
- Barra lateral con conversaciones (crear, renombrar, fijar, eliminar).
- Títulos automáticos generados con el modelo pequeño.
- Render de Markdown, bloques de código y KaTeX.
- Selector de modelo y `config.json` (tema, modelo por defecto).

**Terminado cuando:** al reiniciar la app se conservan todas las conversaciones.

## Fase 2 · RAG local

- "Mis archivos": agregar carpetas y archivos sueltos, y vigilarlos con `notify`.
- Extractores de PDF (pdfium), DOCX, XLSX (calamine), TXT, MD y HTML.
- Chunking de unos 400 tokens con 15 % de traslape, guardando página y sección.
- Embeddings con fastembed (multilingual-e5-small) en segundo plano, con barra de progreso.
- Tablas `chunks`, `chunks_fts` y `chunks_vec`; búsqueda híbrida con fusión **RRF** (BM25 + KNN).
- Inyección de contexto y citas `[N]` validadas por el backend; panel de fuentes.

**Terminado cuando:** con un conjunto de prueba de 20 preguntas sobre PDFs propios, al menos 80 % de las respuestas son correctas y citan la fuente adecuada.

## Fase 3 · Herramientas y bucle agéntico

- Trait `Tool` y registro de herramientas: `search_files`, `read_file` (paginado), `list_dir`, `write_file`, `edit_file` (con diff).
- Llamadas a herramientas con salida restringida (`format`/JSON schema de Ollama).
- Límite de 6 iteraciones, presupuesto de tiempo y detección de llamadas repetidas.
- Sistema de permisos de tres niveles con **tarjeta de confirmación** en la UI.
- Carpeta `evals/` con casos de uso de herramientas y un script para ejecutarlos.

**Terminado cuando:** al menos 90 % de la suite de evaluación encadena "buscar, leer y resumir" sin llamadas inventadas.

## Fase 4 · Router y prompt modular

- Prompt armado por bloques (rol, fecha, reglas, herramientas activas, citas, contexto).
- Router de intención con Qwen3 0.6B o 1.7B (salida JSON con la etiqueta).
- Catálogo diferido: solo se exponen las herramientas de la intención detectada.
- Resumen automático del historial al llegar al 70 % del contexto.

**Terminado cuando:** el prompt de sistema queda por debajo de 2 K tokens y la latencia baja entre 30 y 50 % sin perder calidad en la evaluación.

## Fase 5 · Skills y Office

- Cargador de skills (`skills/<nombre>/SKILL.md` con frontmatter `name`, `description` y `allowed-tools`) y la herramienta `load_skill`.
- Python gestionado con `uv` (instalado en el primer arranque), con helpers JSON por stdin para docx, xlsx, pptx y PDF.
- Vista previa de los archivos generados en el chat.
- Acciones rápidas (`quick_actions/*.md` con `$ARGUMENTS`).
- Skill `create-skill` para que el usuario cree sus propias skills.

**Terminado cuando:** "Hazme un Excel con esta tabla" genera el archivo, lo previsualiza y queda guardado donde pidió el usuario.

## Fase 6 · Proyectos

- Tabla `projects`: personalidad (que se agrega al prompt), banco de archivos propio (RAG filtrado por `project_id`) y skills asignadas.
- Exportar e importar un proyecto como archivo `.zip`.

**Terminado cuando:** dos proyectos con documentos distintos responden sin mezclar las fuentes.

## Fase 7 · Multimodal y voz

- Adjuntar imágenes al chat con un modelo de visión (Gemma 3 4B o Qwen2.5-VL 3B).
- OCR de PDFs escaneados por tramos de páginas, indexado en RAG.
- Dictado con whisper.cpp (botón de micrófono y `NSMicrophoneUsageDescription`).
- Gestor de "Recursos ML": descargar y eliminar modelos y ver el espacio que ocupan.

**Terminado cuando:** se puede preguntar sobre una foto o un escaneo y dictar mensajes sin conexión.

## Fase 8 · Automatización

- Tabla `scheduled_tasks`: expresión cron, zona horaria, prompt e hilo propio.
- Ejecución en segundo plano, notificaciones del sistema, reintentos y conteo de errores consecutivos.
- Pantalla "Programador" para crear, pausar y ver el historial.

**Terminado cuando:** una tarea como "cada lunes a las 9:00, resume los archivos nuevos de la carpeta X" corre sola y avisa al terminar.

## Fase 9 · Avanzado (según prioridad)

- Sub-agentes de solo lectura y map-reduce para documentos largos, con presupuesto y aviso de cobertura parcial.
- Cliente MCP (`rmcp`) para integraciones externas, por ejemplo Microsoft 365, GitHub o calendarios.
- Widgets declarativos (inputs, derived, state, outputs y chart).
- Búsqueda web opcional (desactivada por defecto).
- Paleta de comandos Cmd/Ctrl+K.
- Proveedores alternos: llama.cpp y MLX.
- Empaquetado `.dmg` y `.msi`, firma de código y actualizaciones automáticas firmadas.

---

## Prácticas transversales

- **Evaluación continua:** la carpeta `evals/` tiene preguntas y resultados esperados (RAG, uso de herramientas, formato). Se ejecuta en CI y en cada cambio de modelo o de prompt.
- **Pruebas:** unitarias en Rust (extractores, chunker, permisos) y en Python (helpers de Office).
- **Telemetría local:** métricas de latencia y tokens por segundo en un panel de desarrollador, sin envío a terceros.
- **Versionado:** SemVer y un `CHANGELOG.md` por versión.

## Riesgos principales

| Riesgo | Mitigación |
|---|---|
| Uso de herramientas poco fiable en modelos de 3 a 8 B | Salida restringida, router, pocas herramientas; validarlo pronto (fases 3 y 4) |
| RAM limitada (16 GB) | Un modelo grande cargado a la vez, cuantización Q4 y descarga por inactividad |
| Calidad de extracción en PDFs complejos | pdfium con OCR de respaldo mediante el modelo de visión |
| Tamaño del instalador | Descargar los modelos bajo demanda, no incluirlos en el paquete |
