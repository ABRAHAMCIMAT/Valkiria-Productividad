"""Genera el ícono oficial de Valkiria a partir del logo de VALTRE (riesgo R-09, cerrado).

Fuente: valtre-logo.png (símbolo a color + nombre en blanco en fondo transparente, 1228 x 282).
El ícono usa solo el símbolo, porque el nombre en blanco no se lee en un ícono pequeño: se recorta,
se centra sobre un cuadrado blanco redondeado (rejilla de íconos de macOS) y se exporta en 1024 px.

Uso: uv run --with pillow python tools/desktop/marca/generar_icono.py
Salida: icono-1024.png (fuente para `tauri icon`) y logo.png (256 px, logo dentro de la app).
"""

from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
LADO = 1024
FIN_SIMBOLO = 330  # el nombre en blanco empieza en x = 334 del logo original
MARGEN, RADIO, OCUPACION = 0.09, 0.2, 0.72  # en fracción del lado: rejilla macOS (824/1024)
FONDO = (255, 255, 255, 255)


def simbolo(logo: Image.Image) -> Image.Image:
    """Recorta el símbolo del logo, sin el nombre y sin bordes transparentes."""
    parte = logo.convert("RGBA").crop((0, 0, FIN_SIMBOLO, logo.height))
    caja = parte.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if caja is None:
        raise ValueError("El logo no tiene símbolo visible en la zona esperada")
    return parte.crop(caja)


def icono(logo: Image.Image, lado: int = LADO) -> Image.Image:
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    m, r = round(lado * MARGEN), round(lado * RADIO)
    ImageDraw.Draw(img).rounded_rectangle((m, m, lado - m - 1, lado - m - 1), radius=r, fill=FONDO)
    s = simbolo(logo)
    escala = (lado - 2 * m) * OCUPACION / max(s.size)
    s = s.resize((round(s.width * escala), round(s.height * escala)), Image.LANCZOS)
    img.alpha_composite(s, ((lado - s.width) // 2, (lado - s.height) // 2))
    return img


if __name__ == "__main__":
    grande = icono(Image.open(AQUI / "valtre-logo.png"))
    grande.save(AQUI / "icono-1024.png", optimize=True)
    grande.resize((256, 256), Image.LANCZOS).save(AQUI / "logo.png", optimize=True)
    print("icono-1024.png y logo.png generados")
