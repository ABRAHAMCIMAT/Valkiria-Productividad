# Acta de cierre: Fase F1 · Inferencia local y selección de modelos

> **Borrador en curso.** Se completa en el incremento 1.6. El plan de la fase está en [06 · F1](../../docs/06-plan-desarrollo-incremental.md#f1--inferencia-local-y-selección-de-modelos-3-semanas).

| Campo | Valor |
|---|---|
| Versión | `0.1.0` |
| Periodo | 2026-11-17 a AAAA-MM-DD |
| Commit verificado | pendiente |
| Tag | `fase-1-cierre` (después de `fase-0-cierre-v2`) |
| PR de cierre | pendiente |

## 1. Alcance entregado

| HU | Título | Estado | CA aprobados / total | PRs |
|---|---|---|---|---|
| HU-04 | Detección del perfil de hardware | Pendiente | 0 / 2 | |
| HU-05 | Descarga verificada de modelos | Pendiente | 0 / 3 | |
| HU-06 | Selección de modelos basada en evidencia | Pendiente | 0 / 2 | |

## 2. Equipos del benchmark (incremento 1.0)

Fijados el 2026-11-17. Los runners de GitHub no tienen GPU ni 32 GB, así que el benchmark de HU-06 corre en equipos físicos (R-14).

| Equipo | SO | RAM | Aceleración | Perfil | Estado |
|---|---|---|---|---|---|
| Mac Apple M4 | macOS 27.2+ arm64 | 16 GB | Metal / MLX | Estándar | Disponible |
| Mac Apple M4 o posterior | macOS 27.2+ arm64 | ≥ 32 GB | Metal / MLX | Avanzado | Sin equipo: «no verificado» |
| Windows x64 con GPU NVIDIA | Windows 11 x64 | — | CUDA / Vulkan | Según RAM | Sin equipo: «no verificado» |

Sin equipo físico, un perfil no tiene modelo por defecto en `catalog.yaml` y el Product Owner decide si `0.1.0` sale así (R-14).

## 3. Checklist de evidencias LLMOps

| Etapa | Evidencia | Ubicación | ✔ |
|---|---|---|---|
| L1 Alcance | HU-04 a HU-06 aprobadas y riesgos R-14 a R-18 registrados | `L1-alcance/` | ☐ |
| L2 Datos | *Dataset card* del dataset dorado v1 + SHA-256 + revisión de PII | `L2-datos/` | ☐ |
| L3 Modelos | Runs de `model-selection` + `catalog.yaml` con licencia y SHA-256 | `L3-modelos/` | ☐ |
| L4 Desarrollo | PRs revisados, cobertura ≥ 85 % (líneas nuevas), humo con motor real | `L4-desarrollo/` | ☐ |
| L5 Evaluación | Veredicto del gate y reproducibilidad (CA-06.1) | `L5-evaluacion/` | ☐ |
| L6 Seguridad | Gitleaks, Semgrep, Bandit, pip-audit, Trivy, licencias y SBOM con el motor | `L6-seguridad/` | ☐ |
| L4/L6 Sonar | `sonar-metrics.json` de `main` con el Quality Gate en `OK` | `L4-desarrollo/`, `L6-seguridad/` | ☐ |
| L7 Release | Checksums y notas de `0.1.0` | `L7-release/` | ☐ |
| L9 Mejora | Retrospectiva y backlog ajustado | `L9-mejora/` | ☐ |
| Trazabilidad | `trazabilidad.csv` completo (HU → CA → test → run → commit) | raíz | ☐ |
| Integridad | `manifest.sha256` generado por CI | raíz | ☐ |

## 4. Resultados de los gates

| Métrica | Umbral (Estándar / Avanzado) | Resultado | Run de MLflow | ¿Pasa? |
|---|---|---|---|---|
| TTFT, prompt de 2 K tokens | ≤ 2.0 s / ≤ 1.5 s | | | |
| Velocidad de generación | ≥ 15 / ≥ 20 tok/s | | | |
| RAM máxima de Valkiria | ≤ 9 / ≤ 22 GB | | | |
| Calidad compuesta | ≥ 0.80 / ≥ 0.80 | | | |
| Conexiones en el primer arranque | 0 | | | |

## 5. Excepciones y riesgos aceptados

| ID | Descripción | Responsable | Vence | ADR / Riesgo |
|---|---|---|---|---|

## 6. Aprobaciones (las registra GitHub en el PR de cierre)

Se aprueban en el mismo acto que el acta de F0 (§5).

- [ ] Líder técnico
- [ ] Ingeniero LLMOps
- [ ] Oficial de seguridad VALTRE
- [ ] Product Owner
