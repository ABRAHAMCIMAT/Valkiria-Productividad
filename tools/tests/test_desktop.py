"""HU-01: marca de Valkiria sobre el fork de Jan y prueba de humo."""

import json
import plistlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop"))
import rebrand
import smoke

FORK = rebrand.APP.exists()


@pytest.mark.skipif(not FORK, reason="apps/desktop no existe")
def test_ca_01_marca_aplicada_en_el_repositorio() -> None:
    """El árbol versionado ya tiene la marca: --check no encuentra nada pendiente."""
    assert rebrand.aplicar(solo_verificar=True) == []


@pytest.mark.skipif(not FORK, reason="apps/desktop no existe")
def test_rn_01_1_y_01_4_identidad_en_tauri() -> None:
    conf = json.loads((rebrand.APP / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    assert conf["productName"] == "Valkiria Productividad"
    assert conf["identifier"] == "com.valtre.valkiria"
    assert conf["bundle"]["publisher"] == "VALTRE"


@pytest.mark.skipif(not FORK, reason="apps/desktop no existe")
def test_r_12_macos_minimo_en_info_plist() -> None:
    info = plistlib.loads((rebrand.APP / "src-tauri/Info.plist").read_bytes())
    assert info["LSMinimumSystemVersion"] == rebrand.MACOS_MINIMO == smoke.MACOS_MINIMO == "27.2"


@pytest.mark.skipif(not FORK, reason="apps/desktop no existe")
def test_rn_01_3_sin_updater_analitica_ni_proveedores_remotos_activos() -> None:
    conf = json.loads((rebrand.APP / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    assert conf["plugins"]["updater"]["endpoints"] == []
    assert "posthog" not in json.dumps(conf)
    proveedores = (rebrand.APP / "web-app/src/constants/providers.ts").read_text(encoding="utf-8")
    predefinidos = proveedores[proveedores.index("export const predefinedProviders") :]
    assert "active: true" not in predefinidos
    vite = (rebrand.APP / "web-app/vite.config.ts").read_text(encoding="utf-8")
    assert "raw.githubusercontent.com/janhq" not in vite


@pytest.mark.skipif(not FORK, reason="apps/desktop no existe")
def test_rn_01_2_atribucion_y_licencia() -> None:
    assert "Apache License" in (rebrand.APP / "LICENSE").read_text(encoding="utf-8")
    for idioma in ("es", "en"):
        ajustes = json.loads(
            (rebrand.APP / f"web-app/src/locales/{idioma}/settings.json").read_text(
                encoding="utf-8"
            )
        )
        assert "Jan" in ajustes["general"]["aboutAttribution"]
        assert "VALTRE" in ajustes["general"]["aboutTitle"]


def test_parche_idempotente_y_estricto() -> None:
    p = rebrand.Parche("x", "hola Jan", "hola Valkiria", "prueba")
    assert p.aplicar("di hola Jan") == ("di hola Valkiria", True)
    assert p.aplicar("di hola Valkiria") == ("di hola Valkiria", False)
    with pytest.raises(rebrand.ParcheError, match="prueba"):
        p.aplicar("upstream cambió")


def test_locales_reemplaza_solo_la_palabra_jan(tmp_path: Path) -> None:
    ruta = tmp_path / "es" / "settings.json"
    ruta.parent.mkdir()
    texto = json.dumps({"a": "Ayúdanos a mejorar Jan", "b": "January", "c": ["Jan-v1"]})
    datos = json.loads(rebrand._locales(texto, ruta))
    assert datos["a"] == "Ayúdanos a mejorar Valkiria"
    assert datos["b"] == "January"
    assert datos["c"] == ["Valkiria-v1"]
    assert datos["general"]["aboutAttribution"] == rebrand.ATRIBUCION_ES


def test_proveedores_inactivos() -> None:
    texto = (
        "const otros = { active: true, }\nexport const predefinedProviders = [{ active: true, }]"
    )
    resultado = rebrand._proveedores(texto)
    assert resultado.startswith("const otros = { active: true, }")
    assert resultado.endswith("[{ active: false, }]")


@pytest.mark.parametrize(
    ("direccion", "externa"),
    [
        ("127.0.0.1:1337", False),
        ("[::1]:5000", False),
        ("*:*", False),
        ("0.0.0.0:0", False),
        ("140.82.112.3:443", True),
        ("[2606:4700::1111]:443", True),
        ("api.openai.com:443", True),
        ("::1:80", False),
        (":::0", False),
        ("2606:4700::1111:443", True),
    ],
)
def test_ca_01_3_clasifica_conexiones(direccion: str, externa: bool) -> None:
    assert smoke.es_externa(direccion) is externa


def test_ca_01_1_valida_identidad() -> None:
    buena = {
        "nombre": "Valkiria Productividad",
        "identificador": "com.valtre.valkiria",
        "copyright": "© VALTRE. Basado en Jan (Apache 2.0).",
        "macos_minimo": "27.2",
    }
    assert smoke.validar_identidad(buena, "macos") == []
    errores = smoke.validar_identidad({"nombre": "Jan", "identificador": "jan.ai.app"}, "macos")
    assert len(errores) == 4  # nombre, identificador, macOS mínimo y mención a Jan
    viejo = smoke.validar_identidad({**buena, "macos_minimo": "10.13"}, "macos")
    assert viejo == ["LSMinimumSystemVersion: '10.13' (se espera '27.2')"]
    assert smoke.validar_identidad(
        {"nombre": "Valkiria Productividad", "fabricante": "Otro"}, "windows"
    )


# ---------- CA-01.3 en macOS: registro unificado de Network.framework ----------
def _evento(pid: int, proceso: str, mensaje: str) -> dict[str, object]:
    return {"processID": pid, "processImagePath": f"/x/{proceso}", "eventMessage": mensaje}


WEBKIT = "com.apple.WebKit.Networking"


def test_ca_01_3_registro_atribuye_el_webview_por_pid_de_cliente() -> None:
    """WebKit abre las conexiones del WebView en otro proceso y anota el pid del cliente."""
    eventos = [
        _evento(900, WEBKIT, "[C1 Hostname#fe2e:443 quic, pid: 100, attribution: developer]"),
        _evento(900, WEBKIT, "[C1.1 Hostname#fe2e:443 in_progress (satisfied, interface: en0)]"),
        # Conexión de otra app en el mismo proceso de WebKit: no se atribuye.
        _evento(900, WEBKIT, "[C2 Hostname#aaaa:443 quic, pid: 555]"),
        _evento(900, WEBKIT, "[C2 Hostname#aaaa:443 in_progress (interface: en0)]"),
    ]
    (c,) = smoke.conexiones_registradas(eventos, {100})
    assert (c.proceso, c.pid, c.conexion, c.interfaces, c.externa) == (
        WEBKIT,
        900,
        "C1",
        ["en0"],
        True,
    )


def test_ca_01_3_registro_loopback_no_es_externa() -> None:
    eventos = [
        _evento(100, "Valkiria-Productividad", "nw_endpoint_handler_start [C3 IPv4#ec5f:18765]"),
        _evento(100, "Valkiria-Productividad", "[C3.1 IPv4#ec5f:18765 waiting (interface: lo0)]"),
    ]
    (c,) = smoke.conexiones_registradas(eventos, {100})
    assert c.interfaces == ["lo0"]
    assert not c.externa


def test_ca_01_3_registro_ignora_lineas_sin_conexion_y_no_json() -> None:
    lineas = [
        'Filtering the log data using "process == ..."',
        json.dumps(_evento(100, "Valkiria-Productividad", "Launch Services checkin")),
        "{no es json",
        json.dumps({"processID": "x", "eventMessage": "[C1 a:1 (interface: en0)]"}),
    ]
    eventos = list(smoke.leer_eventos(lineas))
    assert len(eventos) == 2
    assert smoke.conexiones_registradas(eventos, {100}) == []


def test_ca_01_3_predicado_valida_el_ejecutable() -> None:
    predicado = smoke.predicado_red("Valkiria-Productividad")
    assert 'process == "Valkiria-Productividad"' in predicado
    assert f'process == "{WEBKIT}"' in predicado
    # Sin filtro de subsystem: en modo stream descarta los mensajes de WebKit.
    assert "subsystem" not in predicado
    with pytest.raises(ValueError, match="inválido"):
        smoke.predicado_red('x" OR process != "')
