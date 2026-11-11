# ADR-0010 · Seguridad: modelo de amenazas, guardrails y SSDF

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
- Marcos de referencia: OWASP LLM Top 10 (2025), ASVS nivel 2, NIST AI RMF, SSDF y SLSA nivel 3. El detalle está en [04-seguridad](../04-seguridad.md).
- Guardrails locales:
  - **LLM Guard** para entrada, salida y chunks.
  - **Presidio** con reconocedores en español.
  - Modelo guardián pequeño opcional (Qwen3Guard o Granite Guardian).
- Permisos de tres niveles con HITL; `shell` bloqueado por defecto; sandbox de rutas.
- Cadena de suministro: Gitleaks, Semgrep, Bandit, pip-audit, Trivy, Syft (SBOM), OpenSSF Scorecard, atestaciones y commits firmados.

## Consecuencias
- (+) Seguridad verificable por gates automáticos.
- (−) Latencia adicional de los guardrails (unos 50 a 150 ms); se mitiga ejecutándolos en paralelo con el router.
