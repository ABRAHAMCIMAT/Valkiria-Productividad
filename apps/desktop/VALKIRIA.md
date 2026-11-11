# Fork de Jan para Valkiria Productividad

Este directorio contiene **Jan v0.8.8** (commit de upstream `646ab625b9771d0dd6a60f334d41277ef01f1457`),
de Menlo Research, bajo la licencia Apache 2.0 ([`LICENSE`](LICENSE)). Se integra como *git subtree*
([ADR-0001](../../docs/adr/ADR-0001-frontend-fork-jan.md)). Valkiria Productividad no está afiliado a
Menlo Research ni usa la marca Jan en el producto.

## Cómo se mantiene

| Acción | Comando |
|---|---|
| Importar o sincronizar un tag de Jan (trimestral, riesgo R-03) | `tools/desktop/sync-jan.sh v0.X.Y` |
| Aplicar la marca y la configuración de Valkiria | `python3 tools/desktop/rebrand.py` |
| Verificar que no falta nada (lo hace CI) | `python3 tools/desktop/rebrand.py --check` |

`sync-jan.sh` importa el tag **sin** el sitio web de Jan (`docs/`, ~233 MB) ni sus recursos de
marketing. `rebrand.py` falla y señala el parche si upstream cambió alguno de los fragmentos que
modifica, para que nunca quede una marca a medias.

## Desviaciones respecto a Jan

Todas las aplica `tools/desktop/rebrand.py`; no hay otros cambios manuales en este directorio.

| Área | Cambio | Regla |
|---|---|---|
| Identidad | `productName` «Valkiria Productividad», binario `Valkiria-Productividad`, `identifier` `com.valtre.valkiria`, `publisher` VALTRE, versión `0.0.1`, título de ventana, `<title>`, `Cargo.toml` (descripción y autores) | RN-01.1, RN-01.4 |
| Ícono y logo | `src-tauri/icons/icon.png`, `src-tauri/app-icon.png` y `web-app/public/images/jan-logo.png` reemplazados por el ícono **provisional** de `tools/desktop/marca/` (decisión D3, riesgo R-09) | RN-01.1 |
| Textos | La palabra «Jan» en los 18 idiomas de `web-app/src/locales` y en 7 componentes pasa a «Valkiria» | RN-01.1 |
| Acerca de | Tarjeta en *Ajustes → General* con «Valkiria Productividad · VALTRE» y la atribución a Jan bajo Apache 2.0 (es/en; el resto de idiomas usa el inglés) | RN-01.2 |
| Proveedores remotos | Todos los proveedores predefinidos (OpenAI, Anthropic, Gemini, etc.) quedan `active: false` | RN-01.3 |
| Actualizaciones | Updater de Jan desactivado por defecto (`AUTO_UPDATER_DISABLED`), sin endpoints ni clave pública de Jan. El updater de Valkiria llega en F10 (HU-26) | RN-01.3 |
| Catálogo de modelos | Sin descarga del catálogo ni del «modelo recomendado» de Jan desde GitHub; solo se consultan si se define `VALKIRIA_MODEL_CATALOG_URL` / `VALKIRIA_LATEST_MODEL_URL`. El catálogo verificado llega en F1 (HU-05) | RN-01.3 |
| Analítica | PostHog fuera de la CSP. Además, la analítica de Jan solo se inicia si el build define `POSTHOG_KEY`, y Valkiria no la define | RN-01.3 |

## Limitaciones conocidas en F0

- **Motor de inferencia:** el build de CI usa los *stubs* de Jan (`scripts/stub-tauri-resources.mjs`)
  para llama.cpp y MLX. La app abre y muestra la marca, pero no ejecuta modelos locales; el motor real
  se compila desde F1 (HU-04, HU-05).
- **Dependencias de terceros:** Jan v0.8.8 trae ~100 CVE altas o críticas en `yarn.lock` y `Cargo.lock`.
  Se reportan en cada CI y están cubiertas por la excepción **EX-003** (vence el 2026-12-31, riesgo R-13);
  la remediación es parte de F1.
- **Pruebas de Jan:** algunas pruebas unitarias de upstream comprueban textos «Jan» o proveedores activos
  y fallan con la marca aplicada. No forman parte del CI de Valkiria.
- **Sin firma:** los instaladores de CI no están firmados ni notarizados (F10, HU-26).
