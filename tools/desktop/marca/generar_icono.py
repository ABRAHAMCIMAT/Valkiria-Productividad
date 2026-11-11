"""Genera el ícono PROVISIONAL de Valkiria (decisión D3, riesgo R-09).

Se usa hasta recibir el ícono oficial de VALTRE.

Uso: uv run --with pillow python tools/desktop/marca/generar_icono.py
Salida: icono-1024.png (fuente para `tauri icon`) y logo.png (256 px, logo dentro de la app).
"""

from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
LADO = 1024
INICIO, FIN = (49, 46, 129), (124, 58, 237)  # índigo → violeta


def icono(lado: int = LADO) -> Image.Image:
    fondo = Image.new("RGB", (lado, lado))
    pix = fondo.load()
    for y in range(lado):
        for x in range(lado):
            t = (x + y) / (2 * (lado - 1))
            pix[x, y] = tuple(round(a + (b - a) * t) for a, b in zip(INICIO, FIN, strict=True))
    mascara = Image.new("L", (lado, lado), 0)
    margen, radio = lado * 0.06, lado * 0.22
    ImageDraw.Draw(mascara).rounded_rectangle(
        (margen, margen, lado - margen, lado - margen), radius=radio, fill=255
    )
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    img.paste(fondo, mask=mascara)
    d = ImageDraw.Draw(img)
    s = lado / 1024
    puntos = [(270, 290), (390, 290), (512, 640), (634, 290), (754, 290), (568, 760), (456, 760)]
    d.polygon([(x * s, y * s) for x, y in puntos], fill="white")
    return img


if __name__ == "__main__":
    grande = icono()
    grande.save(AQUI / "icono-1024.png")
    grande.resize((256, 256), Image.LANCZOS).save(AQUI / "logo.png")
    print("icono-1024.png y logo.png generados")
