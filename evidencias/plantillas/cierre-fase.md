# Acta de cierre: Fase F<n> · <nombre>

| Campo | Valor |
|---|---|
| Versión | `0.<n>.0` |
| Periodo | AAAA-MM-DD a AAAA-MM-DD |
| Commit de cierre | `<git sha>` |
| Tag | `fase-<n>-cierre` |
| PR de cierre | #<número> |

## 1. Alcance entregado
| HU | Título | Estado | CA aprobados / total | PRs |
|---|---|---|---|---|
| HU-XX | | Hecha / Parcial / Movida | x / y | #.. |

## 2. Checklist de evidencias LLMOps
| Etapa | Evidencia | Ubicación | ✔ |
|---|---|---|---|
| L1 Alcance | HU aprobadas (INVEST) y registro de riesgos actualizado | `L1-alcance/` | ☐ |
| L2 Datos | *Dataset cards* + SHA-256 + revisión de PII | `L2-datos/` | ☐ |
| L3 Modelos | Run de benchmark + `catalog.yaml` con licencia y SHA-256 | `L3-modelos/` | ☐ |
| L4 Desarrollo | Versiones de prompts, PRs revisados, cobertura ≥ 85 % (líneas nuevas) | `L4-desarrollo/` | ☐ |
| L5 Evaluación | Runs de evaluación con veredicto del gate | `L5-evaluacion/` | ☐ |
| L6 Seguridad | Gitleaks, Semgrep, Bandit, pip-audit, Trivy, SBOM y red team | `L6-seguridad/` | ☐ |
| L4/L6 Sonar | `sonar-metrics.json` de `main` con el Quality Gate en `OK` (ratings, *hotspots*, cobertura, duplicación, `ncloc` contra el límite del plan) | `L4-desarrollo/`, `L6-seguridad/` | ☐ |
| L7 Release | Checksums, atestación y notas de versión | `L7-release/` | ☐ / N/A |
| L8 Operación | Métricas del piloto, incidentes | `L8-operacion/` | ☐ / N/A |
| L9 Mejora | Retrospectiva y backlog ajustado | `L9-mejora/` | ☐ |
| Trazabilidad | `trazabilidad.csv` completo (HU → CA → test → run → commit) | raíz | ☐ |
| Integridad | `manifest.sha256` generado por CI | raíz | ☐ |

## 3. Resultados de los gates
| Métrica | Umbral | Resultado | Run de MLflow | ¿Pasa? |
|---|---|---|---|---|
| | | | | |

## 4. Excepciones y riesgos aceptados
| ID | Descripción | Responsable | Vence | ADR / Riesgo |
|---|---|---|---|---|

## 5. Aprobaciones (las registra GitHub en el PR de cierre)
- [ ] Líder técnico
- [ ] Ingeniero LLMOps
- [ ] Oficial de seguridad VALTRE
- [ ] Product Owner (si la fase incluye release)
