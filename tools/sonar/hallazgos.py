"""Lista en Markdown las vulnerabilidades, bugs y hotspots pendientes de la API de Sonar.

Uso: curl .../api/issues/search?... | python3 tools/sonar/hallazgos.py issues
     curl .../api/hotspots/search?... | python3 tools/sonar/hallazgos.py hotspots
"""

import json
import sys


def ruta(componente: str) -> str:
    return componente.split(":", 1)[-1]


def formatear(tipo: str, datos: dict[str, list[dict[str, str]]]) -> list[str]:
    if tipo == "issues":
        return [
            f"- **{i['type']}** `{i['rule']}` {i['severity']} · "
            f"`{ruta(i['component'])}:{i.get('line', '?')}` · {i['message']}"
            for i in datos.get("issues", [])
        ]
    return [
        f"- **HOTSPOT** `{h['ruleKey']}` {h['vulnerabilityProbability']} · "
        f"`{ruta(h['component'])}:{h.get('line', '?')}` · {h['message']}"
        for h in datos.get("hotspots", [])
    ]


def main(argv: list[str]) -> int:
    lineas = formatear(argv[1] if len(argv) > 1 else "issues", json.load(sys.stdin))
    print("\n".join(lineas) if lineas else "- (ninguno)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
