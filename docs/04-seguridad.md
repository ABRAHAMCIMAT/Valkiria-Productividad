# 04 · Seguridad: Valkiria Productividad

Marcos de referencia:
- **OWASP Top 10 para aplicaciones LLM (2025)**
- **OWASP ASVS 5.0** (nivel 2)
- **NIST AI RMF** (funciones Govern, Map, Measure y Manage)
- **NIST SSDF (SP 800-218)**
- **SLSA nivel 3** para la cadena de suministro

## 1. Activos y fronteras de confianza

| Activo | Clasificación | Dónde vive |
|---|---|---|
| Documentos y conversaciones del usuario | Confidencial | `app.db`, `lancedb/`, sistema de archivos |
| Log de auditoría | Integridad crítica | `audit/*.jsonl` |
| Modelos (GGUF/ONNX) | Integridad crítica | `models/` + manifiesto |
| Prompts y configuración del grafo | Integridad | MLflow Prompt Registry |
| Bearer de sesión y API key de Jan | Secreto | Memoria y llavero del SO |
| Binarios e instaladores | Integridad crítica | GitHub Releases |

```
[Usuario] ─(UI)─> [Desktop/Tauri] ─(HTTP 127.0.0.1 + bearer)─> [Valkiria Core] ─(stdio)─> [MCP Tools] ─> [Sistema de archivos permitido]
                         │                                         │
                         └─(127.0.0.1:1337 + API key)─> [llama.cpp]│
   Frontera 1: contenido NO confiable (documentos, web, correo) ───┘   → siempre se trata como datos, nunca como instrucciones
   Frontera 2: red (solo descarga de modelos verificados, actualizaciones y conectores con consentimiento)
```

## 2. Modelo de amenazas (STRIDE)

| Amenaza | Escenario | Controles |
|---|---|---|
| **S**poofing | Otro proceso local llama a la API de Core o de Jan | Solo `127.0.0.1`; puerto efímero; bearer aleatorio de 256 bits por sesión (Tauri lo pasa por stdin, nunca por argumentos); API key de Jan en el llavero |
| **T**ampering | Alguien altera un modelo, un prompt o el log de auditoría | SHA-256 del manifiesto de modelos; Prompt Registry con versiones inmutables; log de auditoría encadenado por hash y verificado al iniciar |
| **R**epudiation | "Yo no aprobé esa acción" | Evento `tool.approved` con usuario del SO, marca de tiempo, hash de los argumentos e `interrupt_id` de un solo uso |
| **I**nformation disclosure | Fuga de datos por telemetría, logs o el propio LLM | Sin telemetría externa; los logs redactan PII con Presidio; las trazas de MLflow guardan hashes del contenido cuando el modo privacidad está activo |
| **D**enial of service | Un documento gigante o un bucle de herramientas | Límites de tamaño; timeouts; 6 llamadas por turno; cuota de tokens por turno; control de RAM |
| **E**levation of privilege | Una inyección de prompt hace que el agente ejecute comandos | Permisos de tres niveles; `shell` desactivado por defecto; sandbox de rutas; las herramientas de escritura siempre en `ask` por defecto |

## 3. Controles por categoría del OWASP LLM Top 10 (2025)

| ID | Riesgo | Controles en Valkiria |
|---|---|---|
| LLM01 | Inyección de prompt (directa e indirecta) | El contenido recuperado se encierra en delimitadores marcados como "datos no confiables"; LLM Guard (`PromptInjection`) en entrada y sobre los chunks; las herramientas con efectos requieren HITL; red teaming con promptfoo y garak en CI |
| LLM02 | Divulgación de información sensible | Presidio para detectar y anonimizar PII en logs y trazas; aislamiento por `project_id` en el retriever (filtro obligatorio); no hay memoria compartida entre proyectos |
| LLM03 | Cadena de suministro | Modelos solo desde un catálogo con licencia y SHA-256; formatos GGUF/safetensors/ONNX (**nunca pickle**); `uv.lock` con hashes; pip-audit, Trivy y Syft (SBOM); atestaciones SLSA en los releases |
| LLM04 | Envenenamiento de datos o del modelo | No hay *fine-tuning* en el dispositivo; los datasets de evaluación están versionados y revisados por PR; ingesta con hash y origen |
| LLM05 | Manejo inadecuado de la salida | El Markdown se sanea en la UI (sin HTML ni scripts); las salidas de herramientas se validan con JSON schema; las rutas se normalizan (anti *path traversal*) |
| LLM06 | Agencia excesiva | Herramientas mínimas por intención; capacidades declaradas; los sub-agentes son de **solo lectura**; HITL; límites de iteración |
| LLM07 | Filtración del system prompt | El prompt no contiene secretos; prueba de red team "extraer el system prompt" (se acepta como riesgo bajo) |
| LLM08 | Debilidades de vectores y embeddings | Filtro de `project_id` y de ACL en cada consulta; borrar un archivo borra sus chunks (prueba de regresión) |
| LLM09 | Desinformación y alucinación | Las citas se validan contra las fuentes; "no sé" cuando la confianza es baja; métricas de *faithfulness* en el gate |
| LLM10 | Consumo ilimitado | Cuota de tokens y de tiempo por turno; *max_tokens*; cola de ingesta con concurrencia limitada |

## 4. Seguridad de la aplicación de escritorio

- **Tauri capabilities:** *allowlist* mínima por ventana; sin `shell:open` arbitrario; el sidecar se declara de forma explícita.
- **CSP estricta** en la web-app: `default-src 'self'; connect-src 'self' http://127.0.0.1:*`; sin `unsafe-eval`.
- El updater verifica la firma minisign y la clave pública va incrustada en el binario.
- **macOS:** *hardened runtime*, notarización y sin excepciones ATS.
- **Windows:** Authenticode y SmartScreen; el instalador evita "per-machine" salvo que TI lo requiera.
- El sidecar corre con el usuario actual, nunca con privilegios elevados.

## 5. Ciclo de desarrollo seguro (SSDF), automatizado en CI

| Etapa | Herramienta | Política de bloqueo |
|---|---|---|
| Secretos en el código | **Gitleaks** (pre-commit + CI) | Cualquier hallazgo bloquea |
| Calidad y seguridad consolidadas | **SonarQube Cloud** en CI y **SonarQube Community** local ([08](08-calidad-sonar.md)), con Bandit, ruff, mypy y ESLint importados | El Quality Gate de código nuevo bloquea: ratings A, 100 % de *hotspots* revisados, duplicación ≤ 3 %, cobertura mínima |
| SAST Python | **Bandit**, **Semgrep** (reglas `python`, `owasp-top-ten`) | Severidad alta bloquea |
| SAST TS | **ESLint** (plugin security) + Semgrep | Severidad alta bloquea |
| Dependencias | **pip-audit**, `npm audit`, **Trivy fs** | CVE ≥ 7.0 sin mitigar bloquea |
| SBOM | **Syft** (CycloneDX) para Python, Node y Rust | Obligatorio en cada release |
| Licencias | **pip-licenses** / license-checker + catálogo de modelos | Licencia no permitida bloquea |
| Red teaming LLM | **promptfoo** (plugins de inyección, PII, *jailbreak*) + **garak** | Tasa de éxito de los ataques ≤ umbral de la fase |
| Postura del repositorio | **OpenSSF Scorecard**, ramas protegidas, revisión obligatoria, commits firmados | Puntaje ≥ 7 |
| Procedencia | GitHub Artifact Attestations (SLSA) | Obligatoria en los releases |

## 6. Privacidad

- Sin telemetría externa; métricas solo locales.
- **Modo privacidad** (activo por defecto): las trazas de MLflow guardan metadatos y hashes, no el texto. El usuario puede activar "trazas completas" para depurar, y esa decisión queda auditada.
- Derecho al olvido: "Eliminar proyecto o archivo" borra filas, chunks, vectores y trazas asociadas, y deja un evento de auditoría que no incluye el contenido.

## 7. Respuesta a incidentes

1. Reporte por `SECURITY.md` (correo de seguridad de VALTRE). Tiempos de respuesta: 72 h para el acuse y 30 días para el parche de severidad alta.
2. Si se compromete una clave de firma: rotación de la clave minisign (el updater admite dos claves durante la transición) y revocación del certificado.
3. Si un modelo resulta vulnerable o con licencia problemática: se retira del catálogo; la app avisa y propone un reemplazo en el siguiente arranque.
4. Postmortem sin culpables, guardado en `evidencias/incidentes/`.
