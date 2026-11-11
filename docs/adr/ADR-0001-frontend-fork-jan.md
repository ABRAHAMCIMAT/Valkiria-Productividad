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

## Implementación en F0 (2026-11-10)
- **Versión:** Jan `v0.8.8` (`646ab625`), la última publicada. Su `LICENSE` es Apache 2.0 con aviso de Menlo Research; la atribución está en [`NOTICE`](../../NOTICE) y en *Ajustes → General*.
- **Importación filtrada:** [`tools/desktop/sync-jan.sh`](../../tools/desktop/sync-jan.sh) importa el tag como *subtree* `--squash` **sin** `docs/` (el sitio web de Jan, ~233 MB) ni sus recursos de marketing. Así el fork pesa 32 MB en lugar de 274 MB y no arrastra la marca Jan.
- **Marca y configuración:** [`tools/desktop/rebrand.py`](../../tools/desktop/rebrand.py) aplica todos los cambios de forma idempotente y falla si upstream modifica un fragmento parchado. La lista de desviaciones está en [`apps/desktop/VALKIRIA.md`](../../apps/desktop/VALKIRIA.md).
- **Hallazgos de la revisión del fork** (todos corregidos por defecto): updater apuntando a los servidores de Jan con su clave pública, PostHog en la CSP, descarga del catálogo de modelos de Jan desde GitHub en el primer arranque y 10 proveedores remotos activos.
- **Build de F0:** binario universal de macOS e instaladores de Windows sin firma (desde el 2026-11-11, macOS solo arm64 con mínimo macOS 27.2; decisión R-12), con el motor de inferencia como *stub*. El motor real se compila desde F1.
- **Riesgo nuevo R-13:** ~100 CVE altas o críticas en las dependencias de terceros de Jan v0.8.8, cubiertas por la excepción EX-003 hasta el 2026-12-31.
