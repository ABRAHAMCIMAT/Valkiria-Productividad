# Valkiria Productividad

Asistente de IA de escritorio de **VALTRE**, 100 % local, basado en modelos LLM pequeños de código abierto: chat, búsqueda sobre tus propios archivos con citas, generación de documentos Office, proyectos y tareas programadas, sin enviar datos fuera del equipo.

## Documentación

| Documento | Contenido |
|---|---|
| [01 · Ingeniería inversa](docs/01-ingenieria-inversa.md) | Análisis de la versión de referencia: stack, datos, sistema agéntico y RAG |
| [02 · Arquitectura propuesta](docs/02-arquitectura-propuesta.md) | Diseño de la nueva solución local, modelos y adaptaciones para modelos pequeños |
| [03 · Plan de desarrollo incremental](docs/03-plan-desarrollo-incremental.md) | Fases 0 a 9 con entregables y criterios de "terminado" |

## Stack previsto

Tauri 2 · Rust · React + TypeScript · Ollama / llama.cpp · Qwen3 / Gemma 3 · fastembed (multilingual-e5-small) · SQLite + FTS5 + sqlite-vec · whisper.cpp · Python (`uv`) para Office/PDF.

## Estado

En planeación. Siguiente paso: **Fase 0**, base Tauri con chat local en streaming.
