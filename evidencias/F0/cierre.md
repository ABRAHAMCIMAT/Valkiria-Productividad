# Acta de cierre: Fase F0 · Fundaciones y gobierno

| Campo | Valor |
|---|---|
| Versión | `0.0.1` (interna) |
| Periodo | 2026-11-10 a 2026-11-11 |
| Commit verificado | `cf0cf48de32cfa7e2a4846a4bf909cadee542114` (gate de fase: [run 43019508658](https://github.com/ABRAHAMCIMAT/Valkiria-Productividad/actions/runs/43019508658)) |
| Tag | `fase-0-cierre` |
| PR de cierre | #11 |

## 1. Alcance entregado

| HU | Título | Estado | CA aprobados / total | PRs |
|---|---|---|---|---|
| HU-01 | Aplicación con marca Valkiria | Hecha | 3 / 3 | #8 |
| HU-02 | Pipeline de integración seguro | Hecha | 3 / 3 | #6, #9 (demo) |
| HU-03 | Registro de experimentos y trazas | Hecha | 3 / 3 | #7 |
| HU-29 | Tablero de calidad del código | Hecha | 5 / 5 | #4, #5 (demo), #10 (demo), #11 |

**Notas por criterio:**
- **CA-02.1 y CA-29.1:** los PRs de demostración #9 y #10 quedaron con su check en rojo. Desde el 2026-11-11 el repositorio es **público** (decisión D1) y el *ruleset* `main` exige PR, prohíbe *force push* y borrado, y requiere los checks Core (3 SO), Seguridad, Evidencia MLflow, SonarQube Cloud y SonarCloud Code Analysis: un PR así ya no se puede fusionar.
- **CA-29.2:** el histórico se completa con los tres análisis de `main` que generan las fusiones de este cierre.
- **CA-29.4:** verificada la privacidad (solo `127.0.0.1:9000`). El análisis local completo se ejecutó después del cierre con Quality Gate en verde (anexo §8).

## 2. Checklist de evidencias LLMOps

| Etapa | Evidencia | Ubicación | ✔ |
|---|---|---|---|
| L1 Alcance | HU de F0 (INVEST) y registro de riesgos actualizado (R-08 a R-13) | `L1-alcance/` | ☑ |
| L2 Datos | No aplica en F0 (sin datasets de evaluación; solo el *fixture* `formato` v1) | — | N/A |
| L3 Modelos | No aplica en F0 (sin modelos; llega en F1) | — | N/A |
| L4 Desarrollo | PRs revisados, JUnit de Core, LLMOps y tools, cobertura ≥ 85 %, `sonar-metrics.json`, prueba de humo de escritorio | `L4-desarrollo/` | ☑ |
| L5 Evaluación | Run de ejemplo etiquetado, gate de tags y exportación de MLflow | `L5-evaluacion/` | ☑ |
| L6 Seguridad | Gitleaks, Semgrep, Bandit, Trivy (propio y del fork), pip-audit, licencias, SBOM CycloneDX y excepciones | `L6-seguridad/` | ☑ |
| L4/L6 Sonar | `sonar-metrics.json` de `main` con el Quality Gate en `OK` y `ncloc` contra el límite del plan | `L4-desarrollo/`, `L6-seguridad/` | ☑ |
| L7 Release | No aplica (F0 no publica release) | — | N/A |
| L8 Operación | No aplica | — | N/A |
| L9 Mejora | Retrospectiva (sección 6) | este documento | ☑ |
| Trazabilidad | `trazabilidad.csv` (HU → RN → CA → prueba/job/demo → resultado → commit) | raíz | ☑ |
| Integridad | `manifest-ci.sha256` generado por CI (run 43019508658) y `manifest.sha256` regenerado tras completar esta acta | raíz | ☑ |

## 3. Resultados de los gates

| Métrica | Umbral | Resultado | Fuente | ¿Pasa? |
|---|---|---|---|---|
| Cobertura de Core | ≥ 85 % | 100 % | `L4-desarrollo/core.xml` | ✔ |
| Cobertura de LLMOps | ≥ 85 % | 100 % | `L4-desarrollo/llmops.xml` | ✔ |
| Cobertura de `tools/` | ≥ 80 % (Sonar) | 96 % | Sonar | ✔ |
| Quality Gate de Sonar en `main` | OK | ver `sonar-metrics.json` | SonarQube Cloud | ✔ |
| Secretos (historial completo) | 0 | 0 | `L6-seguridad/gitleaks.json` | ✔ |
| CVE ≥ 7.0 en código propio | 0 | 0 | `L6-seguridad/trivy.json` | ✔ |
| CVE ≥ 7.0 en el fork de Jan | 0 o excepción vigente | ~100, con EX-003 | `L6-seguridad/trivy-desktop.json` | ✔ con excepción |
| Tags obligatorios en runs de F0 | 100 % | 100 % | `L5-evaluacion/gate.txt` | ✔ |
| Conexiones salientes de la app (5 min, macOS arm64, macOS x64 y Windows x64) | 0 | 0 | `L4-desarrollo/escritorio/` | ✔ |

## 4. Excepciones y riesgos aceptados

| ID | Descripción | Responsable | Vence | ADR / Riesgo |
|---|---|---|---|---|
| ~~EX-001~~ | huey: licencia MIT sin declarar en sus metadatos. **Cerrada:** licencia verificada (anexo §9) | Oficial de seguridad | — | R-07 |
| ~~EX-002~~ | skops: licencia MIT sin declarar en sus metadatos. **Cerrada:** licencia verificada (anexo §9) | Oficial de seguridad | — | R-07 |
| ~~EX-003~~ | Dependencias de terceros de Jan v0.8.8. **Cerrada:** de 100 a 0 hallazgos (anexos §8 y §9) | Oficial de seguridad | — | R-13 |
| — | Motor de inferencia como *stub* en el build de F0 | Líder técnico | F1 | ADR-0001 |
| — | onnxruntime sin *wheels* para Python 3.15. **Mitigado:** el *embedder* de F3 usa torch; solo queda el respaldo RapidOCR de F8 (anexo §10) | Ingeniero LLMOps | Inicio de F8 | R-11, ADR-0002 |
| — | ~~Sin *wheels* para macOS x64 de lancedb, torch y onnxruntime~~ **Cerrado:** sin soporte para Mac Intel (anexo §8) | Product Owner | — | R-12, ADR-0002 |

## 5. Aprobaciones (las registra GitHub en el PR de cierre)

| ✔ | Rol | Responsable | Correo | Alcance de la aprobación |
|---|---|---|---|---|
| [ ] | Líder técnico | Carlos Carballo | carlos.carballo@valtre.com | Acta y alcance de F0 |
| [ ] | Ingeniero LLMOps | Abraham Monsivais | abrahamcimat@me.com | Evidencias L4/L5 y gate de MLflow |
| [ ] | Oficial de seguridad VALTRE | Pedro de Jesús Lara Luna | pedro.lara@valtre.com | Evidencias L6 y cierre de EX-001, EX-002 y EX-003 (anexo §9) |
| [ ] | Product Owner | José Luis Valdez Treviño | luis.valdez@valtre.com | Decisión R-12; D1 resuelta: repositorio público |

**Hallazgos de la prueba de humo resueltos durante F0** (todos de Jan v0.8.8): consulta a `api.github.com` de sus releases en cada arranque, descarga del *embedder* de Hugging Face vía `apps.jan.ai` sin consentimiento, tráfico de fondo de WebView2 hacia Microsoft y `CFBundleIdentifier = jan.ai.app` en su `Info.plist`.

## 6. Retrospectiva (L9)

**Qué funcionó**
- La revisión del fork antes de compilar encontró cuatro fuentes de tráfico saliente hacia Jan (updater, PostHog, catálogo y modelo recomendado) que habrían roto CA-01.3.
- Los escáneres como imágenes fijadas por *digest* y el diagnóstico automático del Quality Gate hicieron rápida la corrección de hallazgos (por ejemplo, la inyección de argumentos en `llmops serve`).
- El spike de dependencias en la primera semana adelantó dos riesgos altos (R-11 y R-12) que habrían aparecido en F3.

**Qué mejorar**
- GitHub retiró `macos-13` y `macos-14`: hay que validar las etiquetas de runner al inicio de cada fase.
- Con el repositorio privado en plan Free se agotaron los minutos de Actions (macOS cuenta ×10) y no había protección de ramas. Se resolvió haciéndolo público (D1).
- Faltaban la firma de commits y el análisis del SonarQube local; ambos se resolvieron después del cierre (anexos §7 y §8).

**Acciones para F1**
1. ~~Cerrar EX-003 antes del 2026-12-31.~~ Hecho (anexo §9). Compilar el motor real de inferencia.
2. ~~Decidir la contingencia de onnxruntime (R-11).~~ Mitigado (anexo §10). R-12 ya está decidido (anexo §8).
3. ~~Correr `tools/desktop/humo-mac-local.sh` en un Mac M4 con macOS 27.2 como evidencia de CA-01.1 y CA-01.3 en macOS.~~ Hecho sobre `main` (anexo §10).
4. ~~Recibir el ícono oficial de VALTRE (R-09).~~ Hecho (anexo §8).
5. ~~Adaptar a la marca las 13 pruebas de `web-app` de Jan que comprueban su comportamiento original.~~ Hecho; la suite corre en CI (anexo §10).

## 7. Anexo posterior al cierre (2026-11-11)

**T-30 · Firma de commits: cerrada.** Con esto se cumple por completo RN-02.3 (PR, revisión, CI en verde y commits firmados).

| Elemento | Estado |
|---|---|
| Firma | SSH con llave ED25519 dedicada (`SHA256:Ciha5HmkNCNSmfmzYabPXoflut2PLb+BveHRd1YZSFU`), registrada como *Signing Key* en `ABRAHAMCIMAT` |
| Configuración de git | `gpg.format=ssh`, `commit.gpgsign=true`, `tag.gpgsign=true`; identidad del repositorio `ABRAHAMCIMAT <abrahamcimat@me.com>` |
| Verificación en GitHub | Commit de prueba `3cbc1ed`: *Verified* (`valid`) |
| *Ruleset* `main` | Regla `required_signatures` activa, junto con PR obligatorio, 7 checks requeridos y bloqueo de *force push* y borrado |

**Hallazgo:** la llave se registró en `ABRAHAMCIMAT`, pero los commits usaban `carlos.carballo@tec.mx`, que GitHub asocia a otra cuenta (`abrahamtec`); por eso salían *Unverified (unknown_key)*. Se resolvió fijando en este repositorio el correo de la cuenta dueña.

Los commits anteriores a este anexo, incluido el tag `fase-0-cierre`, quedan sin firma; la regla aplica a los cambios nuevos. Este anexo modifica `cierre.md`, por lo que `manifest.sha256` se regeneró; `manifest-ci.sha256` conserva el manifiesto original de CI.

## 8. Anexo: pendientes resueltos después del cierre (2026-11-11)

| Pendiente | Resultado | Evidencia |
|---|---|---|
| **CA-29.4** · Análisis local de Sonar | `tools/sonar/scan-local.sh` ahora genera los mismos reportes que CI (pruebas, cobertura, ruff, bandit y mypy). Quality Gate **PASSED**: cobertura 96.5 %, 0 bugs, 0 vulnerabilidades, 0 *code smells*, 0 *hotspots*, 1246 líneas. El servicio solo escucha en `127.0.0.1:9000`, la base de datos no publica puertos y la IP de red no responde | `L4-desarrollo/sonar-local-metrics.json`, `L6-seguridad/sonar-local-privacidad.txt` |
| Hallazgo del análisis local | `python:S8786` (expresión regular superlineal) en `tools/desktop/rebrand.py`: se reemplazó por un filtro de *tokens* con prueba unitaria | commit `4ad1634` |
| **EX-003** · CVE del fork de Jan | De **100 a 6** hallazgos altos o críticos (4 CVE distintas). Se usaron `resolutions` de yarn dentro de la misma versión mayor, se quitaron cinco `devDependencies` de `@janhq/core` sin uso y se subieron vitest a 3.2.6 y `quinn-proto` a 0.11.15. Verificado con `yarn install --immutable`, `build:core`, `build:extensions`, `build:web` y las 171 pruebas de `@janhq/core`. La excepción sigue vigente solo para `zip` (Rust) y `tinypool` (pruebas) | `L6-seguridad/trivy-desktop-remediacion.json`, `apps/desktop/VALKIRIA.md` |
| OpenSSF Scorecard | `publish_results: true`: el repositorio es público y los resultados se publican firmados por OIDC | `.github/workflows/scorecard.yml` |
| **R-12** · Soporte de Mac Intel | **Decidido:** no hay versión para Mac Intel. El mínimo de macOS es **Apple Silicon M4 o posterior con macOS 27.2+**. El `.app` es solo arm64 y declara `LSMinimumSystemVersion` 27.2, que macOS hace cumplir; el chip M4 queda como hardware mínimo soportado, sin bloqueo técnico. CI ya no usa `macos-15-intel` y el *ruleset* deja de exigir `Core · macos-x64`. La prueba de humo de macOS pasa a un Mac M4 (`tools/desktop/humo-mac-local.sh`). La ratifica el Product Owner al aprobar esta acta | ADR-0002, `docs/06` (R-12), `tools/desktop/humo-mac-local.sh` |
| **R-09** · Ícono oficial | El ícono provisional se reemplazó por el símbolo del logo oficial de VALTRE sobre un cuadrado blanco redondeado (rejilla de íconos de macOS). El nombre en blanco del logo no se usa en el ícono porque no se lee en tamaños pequeños. `rebrand.py --check` verifica que el ícono de la app sea el de la marca | `tools/desktop/marca/` (`valtre-logo.png`, `generar_icono.py`) |

Los gates de la sección 3 conservan los valores del commit verificado `cf0cf48`; este anexo registra el estado posterior. `criterios.toml` de F0 conserva los jobs de macOS x64 con los que se cerró la fase; volver a correr su gate sobre un commit nuevo ya no los encontraría. `trazabilidad.csv` actualiza la fila del análisis local de CA-29.4, y `manifest.sha256` se regeneró.

## 9. Anexo: excepciones cerradas (2026-11-11)

Con este anexo F0 queda **sin excepciones de seguridad vigentes** (`security/excepciones.toml` vacío).

| Excepción | Cómo se cerró | Verificación | Evidencia |
|---|---|---|---|
| **EX-001** (huey 3.5.4) y **EX-002** (skops 0.16.0) | Ninguna versión publicada declara licencia en sus metadatos, pero sus wheels traen un `LICENSE` MIT. Quedan como **licencias verificadas** (`[[verificada]]` en `security/licencias.toml`), fijadas a la versión y al SHA-256 del texto del `LICENSE`: si cambia cualquiera de los dos, CI vuelve a bloquear hasta revisarlo. Ya no vencen porque el control es exacto | `politica.py licencias`: 43 paquetes de core y 120 de llmops permitidos, sin excepción | `security/licencias.toml`, `tools/tests/test_politica.py` |
| **EX-003** (6 hallazgos, 4 CVE) | `zip` 0.6/4.6 → 9.5.1 (solo `deflate`), `calamine` 0.23 → 0.38, `tauri` 2.11 → 2.12.5, `tauri-plugin-updater` 2.10 → 2.14.1 y `tinypool` 1.1.1 → 2.2.0. El parser de hojas de cálculo se adaptó a la API nueva de calamine (fechas de libros con sistema 1904) | `trivy fs apps/desktop`: **0** hallazgos. Rust 1.98: `cargo check --all-targets`, 10 pruebas del plugin RAG y 17 del updater. Node 20: 171 pruebas de `@janhq/core`; extensiones y `web-app` con los mismos resultados que antes | `L6-seguridad/trivy-desktop-ex003-cerrada.json`, `apps/desktop/VALKIRIA.md` |

**Tag de cierre.** `fase-0-cierre` apunta al commit con el que se cerró F0 y no se mueve. Cuando estén las cuatro aprobaciones de la sección 5, el Líder técnico crea el tag firmado `fase-0-cierre-v2` sobre el commit de `main` que las registra (`git tag -s fase-0-cierre-v2 -m "F0 cerrada con anexos §7 a §9 y aprobaciones"` y `git push origin fase-0-cierre-v2`).

## 10. Anexo: pendientes resueltos después del cierre (2026-11-12)

| Pendiente | Resultado | Evidencia |
|---|---|---|
| **CA-01.1 y CA-01.3 en macOS** · Prueba de humo en el hardware mínimo | `humo-mac-local.sh --fase F0` sobre el artefacto de `main` (commit `8a5807f`, run 43136052400), ya con el ícono oficial, en un Mac M4 con macOS 27.2. Identidad `com.valtre.valkiria` 0.0.1, la app sigue viva a los 300 s, **0 conexiones externas** y 0 errores | `L4-desarrollo/escritorio/humo-macos-m4/` |
| **R-11** · onnxruntime sin *wheels* `cp315` | onnxruntime 1.31.1 sigue sin ellos. El *embedder* de F3 pasa a `sentence-transformers` 6.3 sobre torch 2.15 (`cp315`): en Python 3.15 y MPS, `multilingual-e5-small` generó *embeddings* de 384 dimensiones y ordenó bien una consulta de prueba (0.896 contra 0.749). Ya no hace falta la contingencia 3.14 en F3. Queda el respaldo RapidOCR de F8, que se revisa al iniciar esa fase. `spike-deps.yml` vigila la pila cada semana en macOS y Windows | ADR-0002 (revisión 2026-11-12), `docs/06` (R-11) |
| **Pruebas de Jan con la marca** (13 de `web-app` y 5 de `llamacpp-extension`) | En `web-app`, 3 comprobaban la marca de Jan (`useAssistant`, `threads` y `headerLabel`) y 10 su consulta de releases (`useReleaseNotes`). Esas 10 fallaban porque `vitest.config.ts` define `AUTO_UPDATER_DISABLED` como la cadena `"false"`, que es verdadera. Ahora fijan el *flag* en `false` y dos pruebas nuevas comprueban RN-01.3: con el updater desactivado no se consulta GitHub. En `llamacpp-extension`, las 5 simulaban un primer arranque sin consentimiento; ahora lo simulan y una prueba nueva comprueba que sin él no se descarga el *embedder*. Tres pruebas que pasaban sin probar nada (dos de `headerLabel` y una de reintento del *embedder*) ahora prueban lo que dicen. Con Node 20 y `TZ=UTC`: **4296 de 4296** en `web-app` y **414 de 414** en extensiones. El job «Pruebas de la app (vitest)» de `desktop.yml` corre core, `web-app` y extensiones | `apps/desktop/web-app/src/**/__tests__/`, `extensions/llamacpp-extension/src/test/`, `.github/workflows/desktop.yml` |
| Paquete de evidencias congelado | Sin cambios a propósito: `criterios.toml`, la sección §3 y la copia de `excepciones.toml` registran el estado del commit verificado `cf0cf48`. Lo vigente está en los anexos §8 a §10, `security/excepciones.toml` (vacío) y `docs/06`. El gate de F1 usará su propio `criterios.toml`, sin jobs de macOS x64 | este anexo |
| Commits sin firma | Aceptado: la regla `required_signatures` aplica desde el anexo §7. El tag `fase-0-cierre-v2` irá firmado | anexo §7 |

**Lo que queda para cerrar F0:** las cuatro aprobaciones de la sección 5 y el tag firmado `fase-0-cierre-v2`. El motor de inferencia real es alcance de F1 (HU-04), no un pendiente de F0. Este anexo agrega archivos al paquete, así que `manifest.sha256` se regeneró; `manifest-ci.sha256` conserva el manifiesto original de CI.
