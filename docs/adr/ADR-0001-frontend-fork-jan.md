# ADR-0001 · Frontend de escritorio: fork de Jan con marca Valkiria

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Contexto
Se requiere una UI de escritorio para macOS y Windows con gestión de modelos locales. El requisito del proyecto es usar **Jan** (`janhq/jan`): Tauri 2, web-app React/TS, extensiones llamacpp, mlx, rag y vector-db, API compatible con OpenAI en `:1337` y cliente MCP. Su licencia es **Apache 2.0** y pide atribución.

## Decisión
Hacer un fork de Jan (v0.8.x) como *git subtree* en `apps/desktop/` y aplicar la marca Valkiria Productividad (VALTRE). Los cambios se concentran en:
1. **Marca:** nombre, íconos, `bundle id` `com.valtre.valkiria` y textos.
2. **`valkiria-extension`:** una extensión TS que registra el proveedor "Valkiria Agent", las tarjetas de confirmación (HITL), el panel de fuentes y el visor de auditoría.
3. **Configuración por defecto:** proveedores en la nube desactivados, servidor `:1337` solo en `127.0.0.1` con API key, y catálogo de modelos restringido.

## Consecuencias
- (+) Gestión de modelos, motor llama.cpp/MLX y UI de chat maduros desde el día 1.
- (+) Se minimizan los cambios al núcleo de Jan, lo que facilita sincronizar con upstream cada trimestre.
- (−) Dependencia de la evolución de Jan (riesgo R-03). Se mitiga con *subtree*, pruebas E2E y lógica propia en la extensión.
- **Obligación legal:** conservar `LICENSE` y `NOTICE`, dar atribución en "Acerca de" y no usar la marca "Jan" en el producto.

## Alternativas descartadas
- **Open WebUI:** es una aplicación web, no de escritorio.
- **LM Studio:** no es open source.
- **UI propia en Tauri:** mayor costo.
