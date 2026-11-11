# 08 · Calidad del código con Sonar

Valkiria usa Sonar en dos modalidades complementarias (decisión en [ADR-0013](adr/ADR-0013-calidad-sonar.md)):

| Modalidad | Para qué | Dónde corre | Analiza |
|---|---|---|---|
| **SonarQube Cloud** (plan gratuito) | **Quality Gate obligatorio** en cada PR y en `main`, decoración de PRs e histórico oficial | GitHub Actions ([`sonar.yml`](../.github/workflows/sonar.yml)) | PRs y `main` |
| **SonarQube Community Build** (open source, local) | Revisar antes de hacer push, sin que el código salga del equipo | Docker en la laptop del desarrollador ([`tools/sonar/`](../tools/sonar/)) | Una foto del árbol de trabajo (la edición Community solo guarda `main`) |

Ambas leen la misma configuración: [`sonar-project.properties`](../sonar-project.properties).

## 1. Qué mide Sonar en Valkiria

| Dimensión | Métricas de Sonar | Fuente de datos |
|---|---|---|
| **Confiabilidad** | Bugs, *reliability rating* | Análisis estático de Python y TS |
| **Seguridad** | Vulnerabilidades, *security hotspots* (revisión obligatoria), *security rating* | Reglas de Sonar más los reportes importados de **Bandit** |
| **Mantenibilidad** | *Code smells*, deuda técnica (`sqale_index`), complejidad ciclomática y cognitiva | Sonar más **ruff**, **mypy** y **ESLint** importados |
| **Duplicación** | % de líneas duplicadas | Sonar |
| **Pruebas** | Cobertura (total y de código nuevo), número de pruebas, fallos | `coverage.xml` y `junit.xml` (pytest) y `lcov.info` (extensión) |
| **Tamaño** | Líneas de código (`ncloc`) | Sonar |

> **Alcance de "rendimiento":** Sonar mide la calidad *estática* del código: complejidad, reglas de eficiencia y uso de recursos. **No mide el rendimiento en ejecución.** La latencia (TTFT, tok/s) y la RAM se miden en el experimento `perf-bench` de MLflow ([05 · §3](05-llmops-trazabilidad.md#3-umbrales-de-los-gates-por-capacidad)). Las dos fuentes juntas forman la evidencia de calidad de cada fase.

**Alcance del análisis:**
- Solo el **código propio** de Valkiria: `core/src`, `apps/desktop/extensions/valkiria-extension/src`, `llmops/` y `tools/`.
- El código del fork de Jan **no** se analiza: no es nuestro, y además consumiría el límite de líneas del plan gratuito.
- El script [`tools/sonar/sources.sh`](../tools/sonar/sources.sh) detecta qué módulos existen.
- Sonar no tiene analizador para Bash ni PowerShell: los scripts de `tools/` se indexan, pero no generan métricas. Las métricas aparecen con el primer código Python o TS.

## 2. Quality Gate

Las condiciones se aplican al **código nuevo** ("Clean as You Code"). Lo que entra no puede empeorar el proyecto.

| Condición (código nuevo) | Umbral | Dónde se aplica |
|---|---|---|
| Cobertura | ≥ 85 % (alineada con la [DoD](06-plan-desarrollo-incremental.md#5-definition-of-done-dod-de-una-hu)) | Gate local "Valkiria"; en Cloud ≥ 80 % (Sonar way) y además `pytest --cov-fail-under=85` en CI |
| Líneas duplicadas | ≤ 3 % | Ambos |
| Reliability rating | A | Ambos |
| Security rating | A | Ambos |
| Maintainability rating | A | Ambos |
| Security hotspots revisados | 100 % | Ambos |

- **SonarQube Cloud:** se usa el gate integrado **Sonar way**. Si el plan permite gates personalizados, se crea "Valkiria" con las condiciones de la tabla.
- **Local:** [`bootstrap-local.sh`](../tools/sonar/bootstrap-local.sh) crea el gate "Valkiria".
- **Propiedad:** `sonar.qualitygate.wait=true` hace que el job de CI **falle** si el gate no pasa. Al marcar el check "SonarQube Cloud" como requerido en la protección de `main`, un PR que no pasa el gate no se puede fusionar.

## 3. Configurar SonarQube Cloud (una sola vez)

Estos pasos los hace el dueño del repositorio, porque requieren iniciar sesión en Sonar y GitHub.

1. Entra a <https://sonarcloud.io> con tu cuenta de GitHub e **importa la organización** de GitHub donde vive el repo. Autoriza la GitHub App de SonarQube Cloud **solo** para `Valkiria-Productividad`.
2. Elige el **plan Free** (repos privados hasta unas 50 000 líneas y 5 usuarios). Confirma el límite vigente en la pantalla de facturación.
3. **Analyze new project** → `Valkiria-Productividad`. En *Administration → Analysis Method* **desactiva "Automatic Analysis"**, porque el análisis lo hace CI y las dos cosas no pueden convivir.
4. En *Administration → New Code* elige **Reference branch = `main`**.
5. Genera un token en *My Account → Security* (tipo *Project Analysis Token* si está disponible).
6. En GitHub, en el repo, ve a *Settings → Secrets and variables → Actions* y crea:

   | Tipo | Nombre | Valor |
   |---|---|---|
   | Secret | `SONAR_TOKEN` | El token del paso 5 |
   | Variable | `SONAR_ORGANIZATION` | La clave de la organización en Sonar (por ejemplo, `abrahamcimat`) |
   | Variable | `SONAR_PROJECT_KEY` | La clave del proyecto (por ejemplo, `ABRAHAMCIMAT_Valkiria-Productividad`) |

   Desde la terminal:
   ```bash
   gh secret set SONAR_TOKEN
   gh variable set SONAR_ORGANIZATION --body "<org>"
   gh variable set SONAR_PROJECT_KEY  --body "<clave>"
   ```
7. Cuando exista el primer código (F0), en *Settings → Branches → main* agrega el check **"SonarQube Cloud"** como requerido.

Mientras falte la configuración, o mientras no haya código propio, el workflow termina en verde con un aviso, para no bloquear el trabajo de documentación.

## 4. Usar SonarQube Community en local

**Requisitos:**
- Docker Desktop.
- Unos 3.5 GB de RAM libres mientras está encendido. Apágalo cuando no lo uses para respetar el presupuesto de memoria de [02 · §5](02-revision-arquitectura-azure.md#5-presupuesto-de-memoria-máximo-32-gb).
- En Windows, además, Git for Windows (aporta `bash`).

```bash
# 1) Configurar la contraseña de la base de datos (el archivo .env no se versiona)
cp tools/sonar/.env.example tools/sonar/.env   # edita SONAR_DB_PASSWORD

# 2) Encender (solo escucha en http://127.0.0.1:9000)
docker compose -f tools/sonar/docker-compose.yml --env-file tools/sonar/.env up -d

# 3) Primera vez: entra a http://127.0.0.1:9000 (admin/admin → cambia la contraseña),
#    genera un token de administrador y crea el proyecto con el gate "Valkiria"
SONAR_ADMIN_TOKEN=<token-admin> tools/sonar/bootstrap-local.sh

# 4) Guarda un token de análisis en el llavero (macOS) y analiza
security add-generic-password -a "$USER" -s valkiria-sonar-local -w <token-analisis>
tools/sonar/scan-local.sh            # en Windows: pwsh tools/sonar/scan-local.ps1

# 5) Apagar
docker compose -f tools/sonar/docker-compose.yml down
```

Antes de analizar, genera los reportes de pruebas y linters (los mismos comandos que en CI, sección *Reportes de Core* de [`sonar.yml`](../.github/workflows/sonar.yml)) para que Sonar muestre la cobertura y los hallazgos importados.

## 5. Requisitos para los módulos (a partir de F0)

Para que el análisis tenga datos, **Valkiria Core** debe incluir en su grupo de desarrollo (`uv add --dev`) estos paquetes: `pytest`, `pytest-cov`, `ruff`, `mypy` y `bandit`.

La **valkiria-extension** debe tener `package-lock.json` y un script `test:coverage` que escriba `reports/lcov.info`.

## 6. Trazabilidad y evidencias

- Cada ejecución en CI exporta `sonar-metrics.json` como artefacto, con 90 días de retención. El archivo incluye el estado del gate, las métricas, el `git_sha` y la rama o el PR. Lo genera [`export-metrics.sh`](../tools/sonar/export-metrics.sh).
- En el **cierre de fase**, el *workflow* de gate copia el `sonar-metrics.json` de `main` en:
  - `evidencias/F<n>/L4-desarrollo/`: mantenibilidad, cobertura y duplicación.
  - `evidencias/F<n>/L6-seguridad/`: vulnerabilidades, *hotspots* y *security rating*.
- El acta de cierre registra el estado del Quality Gate ([plantilla](../evidencias/plantillas/cierre-fase.md)).
- Una excepción al gate (por ejemplo, un *hotspot* marcado como "seguro") debe llevar su justificación en Sonar y un registro de riesgo con su vencimiento.
