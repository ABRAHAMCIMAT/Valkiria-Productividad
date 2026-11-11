# ADR-0008 · Integración entre la UI y Valkiria Core

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
Tres canales:
1. **HTTP local** `127.0.0.1:{puerto efímero}` con **bearer por sesión**. Tauri genera 256 bits y los entrega al sidecar por stdin.
   - `/v1/chat/completions`, compatible con OpenAI, para el proveedor "Valkiria Agent".
   - `/v1/agent/resume`, para el HITL.
   - `/v1/audit`.
2. **MCP stdio:** el servidor de herramientas Valkiria se expone al cliente MCP de Jan y al agente mediante `langchain-mcp-adapters`.
3. **Eventos SSE:** progreso de ingesta y notificaciones.

CORS restringido al origen de Tauri; sin canales en `0.0.0.0`.

## Consecuencias
- (+) La UI de Jan funciona sin cambios en su núcleo; el HITL queda en la extensión.
- (−) Hay que mantener la compatibilidad OpenAI del endpoint; se cubre con pruebas de contrato.
