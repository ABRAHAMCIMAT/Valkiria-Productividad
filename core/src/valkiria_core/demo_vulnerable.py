"""DEMO CA-29.1: código vulnerable a propósito para comprobar que el Quality Gate bloquea. No fusionar."""

import hashlib
import subprocess


def ejecutar(comando_usuario: str) -> str:
    """Inyección de comandos: shell=True con entrada externa."""
    return subprocess.run(comando_usuario, shell=True, capture_output=True, text=True).stdout  # noqa: S602


def huella(password: str) -> str:
    """Hash débil para una contraseña."""
    return hashlib.md5(password.encode()).hexdigest()  # noqa: S324


def conectar() -> dict[str, str]:
    """Credencial escrita en el código."""
    return {"usuario": "admin", "password": "Valkiria2026!"}  # noqa: S105
