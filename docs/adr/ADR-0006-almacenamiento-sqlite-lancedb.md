# ADR-0006 · Almacenamiento: SQLite (relacional) + LanceDB (vectorial e híbrido)

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
- **SQLite** en modo WAL, con SQLAlchemy 2 y migraciones **Alembic**, para conversaciones, proyectos, permisos y tareas.
- **LanceDB** embebido (Apache 2.0) para chunks: vector, índice FTS y búsqueda híbrida con RRF, y filtros por metadatos (`project_id`, `source`).
- Puerto `VectorStorePort`, con adaptadores alternos para Qdrant o pgvector en el modo equipo.

## Alternativas
- **SQLite + sqlite-vec:** el enfoque de la versión de referencia; tiene menos soporte híbrido en Python.
- **Chroma:** menos control del FTS.
- **Qdrant embebido (local mode):** pensado para desarrollo.

## Consecuencias
- (+) Sin servidores, búsqueda híbrida nativa y un camino de escalamiento claro.
- (−) Dos almacenes; la consistencia se garantiza con una ingesta idempotente por hash y una reconciliación al iniciar.
