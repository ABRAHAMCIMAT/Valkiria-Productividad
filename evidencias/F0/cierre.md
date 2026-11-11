# Acta de cierre: Fase F0 · Fundaciones y gobierno

| Campo | Valor |
|---|---|
| Versión | `0.0.1` (interna) |
| Periodo | 2026-11-10 a 2026-11-11 |
| Commit de cierre | se completa al fusionar el PR de cierre |
| Tag | `fase-0-cierre` |
| PR de cierre | #11 |

## 1. Alcance entregado

| HU | Título | Estado | CA aprobados / total | PRs |
|---|---|---|---|---|
| HU-01 | Aplicación con marca Valkiria | __HU01_ESTADO__ | __HU01_CA__ / 3 | #8 |
| HU-02 | Pipeline de integración seguro | Hecha | 3 / 3 | #6, #9 (demo) |
| HU-03 | Registro de experimentos y trazas | Hecha | 3 / 3 | #7 |
| HU-29 | Tablero de calidad del código | Parcial | 4 / 5 | #4, #5 (demo), #10 (demo), #11 |

**Notas por criterio:**
- **CA-02.1 y CA-29.1:** los PRs de demostración #9 y #10 quedan con su check en rojo. GitHub todavía **no impide la fusión** porque el repositorio es privado en plan Free y no admite reglas de protección (riesgo R-08, decisión D1 pendiente).
- **CA-29.2:** el histórico se completa con los tres análisis de `main` que generan las fusiones de este cierre.
- **CA-29.4:** verificada la privacidad (solo `127.0.0.1:9000`). Falta el análisis local completo, que requiere que el responsable cree `SONAR_LOCAL_TOKEN`.

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
| Integridad | `manifest.sha256` generado por `tools/evidencias/armar.sh` | raíz | ☑ |

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
| Conexiones salientes de la app (5 min) | 0 | __EGRESS__ | `L4-desarrollo/escritorio/` | __EGRESS_OK__ |

## 4. Excepciones y riesgos aceptados

| ID | Descripción | Responsable | Vence | ADR / Riesgo |
|---|---|---|---|---|
| EX-001 | huey: licencia MIT sin declarar en sus metadatos | Oficial de seguridad | 2027-05-10 | R-07 |
| EX-002 | skops: licencia MIT sin declarar en sus metadatos | Oficial de seguridad | 2027-05-10 | R-07 |
| EX-003 | ~100 CVE altas o críticas en dependencias de terceros de Jan v0.8.8 | Oficial de seguridad | 2026-12-31 | R-13 |
| — | `main` sin reglas de protección (repo privado en plan Free) | Líder técnico | Decisión D1 | R-08 |
| — | Motor de inferencia como *stub* en el build de F0 | Líder técnico | F1 | ADR-0001 |
| — | onnxruntime sin *wheels* para Python 3.15 | Ingeniero LLMOps | Antes de F3 | R-11, ADR-0002 |
| — | Sin *wheels* para macOS x64 de lancedb, torch y onnxruntime | Product Owner | Antes de F3 | R-12, ADR-0002 |
| — | Commits sin firma (T-30 pendiente) | Cada desarrollador | Inicio de F1 | RN-02.3 |

## 5. Aprobaciones (las registra GitHub en el PR de cierre)
- [ ] Líder técnico
- [ ] Ingeniero LLMOps
- [ ] Oficial de seguridad VALTRE (incluye aprobar EX-003)
- [ ] Product Owner (decisiones D1 y R-12)

## 6. Retrospectiva (L9)

**Qué funcionó**
- La revisión del fork antes de compilar encontró cuatro fuentes de tráfico saliente hacia Jan (updater, PostHog, catálogo y modelo recomendado) que habrían roto CA-01.3.
- Los escáneres como imágenes fijadas por *digest* y el diagnóstico automático del Quality Gate hicieron rápida la corrección de hallazgos (por ejemplo, la inyección de argumentos en `llmops serve`).
- El spike de dependencias en la primera semana adelantó dos riesgos altos (R-11 y R-12) que habrían aparecido en F3.

**Qué mejorar**
- GitHub retiró `macos-13` y `macos-14`: hay que validar las etiquetas de runner al inicio de cada fase.
- El repositorio privado en plan Free impide cerrar del todo RN-02.3 y RN-29.3, y encarece los minutos de macOS.
- Faltan la firma de commits y los tokens del SonarQube local.

**Acciones para F1**
1. Decidir D1 (repo público o GitHub Pro) y activar la protección de `main` con los checks requeridos.
2. Remediar las CVE de runtime del fork (EX-003) y compilar el motor real de inferencia.
3. Decidir el soporte de macOS Intel (R-12) y la contingencia de onnxruntime (R-11).
4. Configurar la firma de commits y completar el análisis local de Sonar (CA-29.4).
5. Recibir el ícono oficial de VALTRE (R-09).
