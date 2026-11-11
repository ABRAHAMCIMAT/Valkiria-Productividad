"""Tags obligatorios de trazabilidad (RN-03.1, RN-03.2 y docs/05 §4.2)."""

from __future__ import annotations

import os
import platform
import re

# Solo se invoca git con argumentos fijos.
import subprocess  # nosec B404
from collections.abc import Mapping

GIT_SHA = "git.sha"
MODEL_SHA256 = "model.sha256"
OBLIGATORIOS = ("valkiria.version", GIT_SHA, "phase", MODEL_SHA256, "profile", "os")
PREFIJO_PROMPT = "prompt."
SUFIJO_PROMPT = ".version"
PERFILES = ("estandar", "avanzado", "ci")

_FORMATOS = {
    "phase": re.compile(r"^F(\d|1[01])$"),
    "hu": re.compile(r"^HU-\d{2}$"),
    GIT_SHA: re.compile(r"^[0-9a-f]{7,40}$"),
    MODEL_SHA256: re.compile(r"^[0-9a-f]{64}$"),
    "os": re.compile(r"^(macos|windows|linux)-(arm64|x64)$"),
}


def os_tag(system: str | None = None, machine: str | None = None) -> str:
    """Etiqueta de SO de las trazas, por ejemplo ``macos-arm64``."""
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    nombre = {"darwin": "macos"}.get(system, system)
    arq = {"aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(machine, machine)
    return f"{nombre}-{arq}"


def git_sha() -> str:
    """SHA del commit: ``GITHUB_SHA`` en CI o ``git rev-parse HEAD`` en local."""
    if sha := os.environ.get("GITHUB_SHA"):
        return sha
    try:
        # Comando fijo, sin entrada del usuario.
        salida = subprocess.run(  # nosec B603 B607
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except OSError, subprocess.SubprocessError:
        return ""
    return salida.stdout.strip()


def construir(
    *,
    phase: str,
    model_sha256: str,
    prompts: Mapping[str, int],
    profile: str,
    valkiria_version: str,
    hu: str | None = None,
    sha: str | None = None,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Construye el conjunto de tags de un run o traza."""
    tags = {
        "valkiria.version": valkiria_version,
        GIT_SHA: sha if sha is not None else git_sha(),
        "phase": phase,
        MODEL_SHA256: model_sha256,
        "profile": profile,
        "os": os_tag(),
    }
    if hu:
        tags["hu"] = hu
    tags |= {f"{PREFIJO_PROMPT}{n}{SUFIJO_PROMPT}": str(v) for n, v in prompts.items()}
    tags |= dict(extra or {})
    return tags


def faltantes(tags: Mapping[str, str]) -> list[str]:
    """Devuelve los problemas de un conjunto de tags; vacío si cuenta como evidencia (RN-03.2)."""
    problemas = [f"falta el tag {t}" for t in OBLIGATORIOS if not str(tags.get(t, "")).strip()]
    prompts = [k for k in tags if k.startswith(PREFIJO_PROMPT) and k.endswith(SUFIJO_PROMPT)]
    if not prompts:
        problemas.append("falta al menos un tag prompt.<nombre>.version")
    for k in prompts:
        if not str(tags[k]).isdigit():
            problemas.append(f"el tag {k} debe ser un número de versión")
    for clave, patron in _FORMATOS.items():
        valor = str(tags.get(clave, "")).strip()
        if valor and not patron.match(valor):
            problemas.append(f"el tag {clave} tiene un formato no válido: {valor!r}")
    perfil = str(tags.get("profile", "")).strip()
    if perfil and perfil not in PERFILES:
        problemas.append(f"el tag profile debe ser uno de {', '.join(PERFILES)}: {perfil!r}")
    return problemas
