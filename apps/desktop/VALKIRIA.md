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

Las de marca y privacidad las aplica `tools/desktop/rebrand.py`. Los únicos cambios manuales son los de dependencias de la sección siguiente.

| Área | Cambio | Regla |
|---|---|---|
| Identidad | `productName` «Valkiria Productividad», binario `Valkiria-Productividad`, `identifier` `com.valtre.valkiria`, `publisher` VALTRE, versión `0.0.1`, título de ventana, `<title>`, `Cargo.toml` (descripción y autores) | RN-01.1, RN-01.4 |
| Ícono y logo | `src-tauri/icons/icon.png`, `src-tauri/app-icon.png` y `web-app/public/images/jan-logo.png` reemplazados por el ícono **provisional** de `tools/desktop/marca/` (decisión D3, riesgo R-09) | RN-01.1 |
| Textos | La palabra «Jan» en los 18 idiomas de `web-app/src/locales` y en 7 componentes pasa a «Valkiria» | RN-01.1 |
| Acerca de | Tarjeta en *Ajustes → General* con «Valkiria Productividad · VALTRE» y la atribución a Jan bajo Apache 2.0 (es/en; el resto de idiomas usa el inglés) | RN-01.2 |
| Proveedores remotos | Todos los proveedores predefinidos (OpenAI, Anthropic, Gemini, etc.) quedan `active: false` | RN-01.3 |
| Actualizaciones | Updater de Jan desactivado por defecto (`AUTO_UPDATER_DISABLED`), sin endpoints ni clave pública de Jan. El updater de Valkiria llega en F10 (HU-26) | RN-01.3 |
| Catálogo de modelos | Sin descarga del catálogo ni del «modelo recomendado» de Jan desde GitHub; solo se consultan si se define `VALKIRIA_MODEL_CATALOG_URL` / `VALKIRIA_LATEST_MODEL_URL`. El catálogo verificado llega en F1 (HU-05) | RN-01.3 |
| Notas de versión | Jan consultaba `api.github.com/repos/janhq/jan/releases` en cada arranque; ahora solo con el updater activo | RN-01.3 |
| Embedder de RAG | Jan descargaba `all-MiniLM-L6-v2` de Hugging Face (vía `apps.jan.ai`) en el primer arranque sin consentimiento; ahora solo tras aceptar la configuración inicial | RN-01.3 |
| WebView2 (Windows) | Arranca sin red de fondo, actualización de componentes, SmartScreen ni pings hacia Microsoft (`additionalBrowserArgs`) | RN-01.3 |
| `Info.plist` (macOS) | `CFBundleIdentifier` y `CFBundleURLName` pasan a `com.valtre.valkiria`; el `Info.plist` propio de Jan sobrescribía el `identifier` de Tauri. El esquema `jan://` se conserva porque lo usan internamente los callbacks | RN-01.4 |
| Analítica | PostHog fuera de la CSP. Además, la analítica de Jan solo se inicia si el build define `POSTHOG_KEY`, y Valkiria no la define | RN-01.3 |

## Dependencias (remediación de EX-003, 2026-11-11)

Cambios manuales para reducir los hallazgos de terceros de 100 a 6 (4 CVE distintas). Al sincronizar un tag nuevo de Jan
hay que conservarlos o comprobar que upstream ya los resolvió (`trivy fs apps/desktop`).

| Archivo | Cambio | Motivo |
|---|---|---|
| `package.json` | `resolutions` por descriptor hacia la versión corregida **de la misma versión mayor**: brace-expansion, dompurify, flatted, glob, ip-address, js-yaml, lodash-es, minimatch, nanoid, picomatch, postcss, preact, rollup, seroval, source-map-js, tar 7, vite 7 | CVE altas o críticas con corrección compatible por semver |
| `core/package.json` | Fuera `@npmcli/arborist`, `pacote`, `request`, `request-progress` y `happy-dom`: son `devDependencies` que ningún archivo usa (las pruebas corren con `jsdom`) | Traían tar 6, pacote 18, sigstore 2, form-data 2.3 y happy-dom 20 |
| `*/package.json` | `vitest`, `@vitest/ui` y `@vitest/coverage-v8` de 2.1.9 / 3.2.4 a 3.2.6 en todos los workspaces | CVE-2026-47429; además desaparecen vite 5 y vite-node 2 |
| `src-tauri/utils/Cargo.lock`, `src-tauri/plugins/tauri-plugin-llamacpp/Cargo.lock` | `quinn-proto` 0.11.14 → 0.11.15 (mismas dependencias; el `Cargo.lock` principal ya usaba 0.11.16) | GHSA-4w2j-m93h-cj5j |

Verificado en Node 20 y yarn 4.5.3: `yarn install --immutable`, `build:core`, `build:extensions`,
`build:web` y las 171 pruebas de `@janhq/core` pasan.

## Limitaciones conocidas en F0

- **Motor de inferencia:** el build de CI usa los *stubs* de Jan (`scripts/stub-tauri-resources.mjs`)
  para llama.cpp y MLX. La app abre y muestra la marca, pero no ejecuta modelos locales; el motor real
  se compila desde F1 (HU-04, HU-05).
- **Dependencias de terceros:** quedan 6 hallazgos altos o críticos (de 100; 4 CVE distintas): `zip` en Rust, que exige subir
  tauri, tauri-plugin-updater y calamine, y `tinypool`, solo de pruebas. Se reportan en cada CI y están
  cubiertas por la excepción **EX-003** acotada (vence el 2026-12-31, riesgo R-13); el resto es parte de F1.
- **Pruebas de Jan:** 13 de las 4294 pruebas de `web-app` fallan con la marca aplicada porque comprueban
  el comportamiento original de Jan (etiqueta «Jan», consulta de releases a GitHub, asistente por defecto).
  No forman parte del CI de Valkiria; se adaptan en F1.
- **Sin firma:** los instaladores de CI no están firmados ni notarizados (F10, HU-26).
