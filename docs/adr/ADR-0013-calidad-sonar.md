# ADR-0013 · Calidad del código con Sonar (Cloud + Community local)

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Contexto
Antes de iniciar el desarrollo se requiere medir y controlar de forma continua la calidad, la seguridad y la mantenibilidad del código, con estadísticas históricas y bloqueo de cambios que degraden el proyecto. El repositorio es privado.

## Decisión
Usar **ambas** modalidades de Sonar:
1. **SonarQube Cloud, plan gratuito** (repos privados de hasta unas 50 000 líneas y 5 usuarios), como **Quality Gate obligatorio** en GitHub Actions: análisis de PRs y de `main`, decoración de PRs y exportación de métricas como evidencia.
2. **SonarQube Community Build** (LGPL, open source), autoalojado con Docker solo en `127.0.0.1`, para el análisis local antes del push.

Detalles de la decisión:
- **Configuración común:** `sonar-project.properties`.
- **Alcance:** solo el código propio. El fork de Jan queda excluido, por propiedad del código y por el límite de líneas.
- **Reportes importados:** cobertura y JUnit de pytest, ruff, mypy y Bandit en Python; lcov y ESLint en TypeScript.
- **Versiones fijadas:**
  - `SonarSource/sonarqube-scan-action` v8.4.1, por SHA.
  - `sonarqube:26.10.0.133078-community`.
  - `sonarsource/sonar-scanner-cli:12.2`.
  - `postgres:17.11`.

## Consecuencias
- (+) Métricas históricas, comentarios en los PRs y un gate que bloquea la fusión; evidencia exportable por fase.
- (+) Un análisis local sin dependencia de la red para revisar antes del push.
- (−) **Privacidad del código:** SonarQube Cloud recibe el código fuente (no los datos de los usuarios). Es aceptable porque Valkiria procesa los datos de los usuarios solo en el equipo; si VALTRE lo prohíbe, se sustituye Cloud por un SonarQube autoalojado en un servidor.
- (−) **Límite de unas 50 000 líneas** en el plan gratuito. Se vigila `ncloc` en cada cierre de fase y, al llegar al 80 % del límite, se decide entre ajustar exclusiones, pasar a un plan pago o autoalojar.
- (−) El SonarQube local consume unos 3.5 GB de RAM mientras corre; se enciende solo cuando se usa.
- (−) La edición Community local solo conserva `main`, así que no sustituye al gate de los PRs.
- **"Rendimiento":** Sonar no mide el rendimiento en ejecución; eso queda en el experimento `perf-bench` de MLflow (ADR-0005).

## Alternativas descartadas
- **Solo Community local:** no decora los PRs ni es accesible desde CI sin un servidor.
- **Community + plugin no oficial de ramas (mc1arke):** no tiene soporte del fabricante y añade riesgo de mantenimiento.
- **Qodana:** no se eligió.
- **DeepSource:** no se eligió.
