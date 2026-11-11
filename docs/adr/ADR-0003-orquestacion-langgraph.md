# ADR-0003 · Orquestación con LangGraph y LangChain v1 (sin LangSmith)

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Contexto
Se requiere "lo mejor del stack de LangChain" en una solución open source, local y con mini LLMs.

## Decisión
- **LangGraph:** `StateGraph`, *checkpointer* SQLite, `interrupt` para HITL, subgrafos para sub-agentes de solo lectura y `Store` para la memoria por proyecto.
- **LangChain v1:**
  - `create_agent` con middleware: `HumanInTheLoopMiddleware`, `SummarizationMiddleware`, PII, límite de llamadas a herramientas y *fallback* de modelo.
  - `langchain-openai` (`ChatOpenAI` con `base_url` apuntando al servidor local).
  - `langchain-mcp-adapters`, `langchain-text-splitters` e integraciones de LanceDB y Docling.
- **No se usan** LangSmith, LangGraph Platform ni LangGraph Studio, porque son propietarios o requieren una cuenta. La observabilidad la cubre MLflow (ADR-0005).
- Las versiones se fijan en `uv.lock`; se actualizan de forma mensual mediante un PR con la evaluación completa.

## Consecuencias
- (+) HITL, resumen y reanudación ya resueltos y probados.
- (−) La API de LangChain evoluciona rápido; se mitiga con puertos y adaptadores (el dominio no importa LangChain) y pruebas de contrato.
