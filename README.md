# Valkiria Productividad

Asistente de IA de escritorio de **VALTRE** para **macOS y Windows**, 100 % local y basado en **mini LLMs gratuitos de código abierto**. Ofrece:
- chat sobre tus propios documentos, con citas verificables;
- un agente con herramientas bajo tu control;
- creación de documentos Office;
- proyectos aislados y tareas programadas.

Todo esto sin enviar datos fuera del equipo y optimizado para laptops de hasta 32 GB de RAM.

## Arquitectura en una línea

**Fork de Jan** (Tauri, React y llama.cpp/MLX) → **Valkiria Core** (Python 3.15, FastAPI, LangGraph y LangChain v1, LanceDB, Docling) → **MLflow 3** para LLMOps (trazas, Prompt Registry, evaluación y evidencias por fase).

## Documentación

| Documento | Contenido |
|---|---|
| [01 · Ingeniería inversa](docs/01-ingenieria-inversa.md) | Análisis de la versión de referencia |
| [02 · Revisión de la arquitectura basada en Azure](docs/02-revision-arquitectura-azure.md) | Diagnóstico, mapeo de Azure a open source, catálogo de mini LLMs y presupuesto de RAM |
| [03 · Arquitectura de referencia](docs/03-arquitectura-referencia.md) | C4, grafo del agente, flujos, contratos, datos, confiabilidad, escalabilidad y despliegue |
| [04 · Seguridad](docs/04-seguridad.md) | STRIDE, OWASP LLM Top 10, SSDF en CI y privacidad |
| [05 · LLMOps y trazabilidad](docs/05-llmops-trazabilidad.md) | Ciclo L1 a L9, gates, auditoría y evidencias de cierre |
| [06 · Plan de desarrollo incremental](docs/06-plan-desarrollo-incremental.md) | Fases F0 a F11, DoR, DoD y riesgos |
| [07 · Historias de usuario](docs/07-historias-usuario.md) | 29 HU con análisis INVEST y versión mejorada |
| [08 · Calidad del código con Sonar](docs/08-calidad-sonar.md) | SonarQube Cloud (Quality Gate en CI) y Community local |
| [ADR](docs/adr/README.md) | 13 decisiones de arquitectura |
| [Evidencias](evidencias/README.md) | Paquetes y plantillas de cierre de fase |

## Atribución

La interfaz de escritorio deriva de [Jan](https://github.com/janhq/jan), de Menlo Research, bajo la licencia Apache 2.0.

## Estado

En planeación. Siguiente paso: **F0 · Fundaciones y gobierno**.
