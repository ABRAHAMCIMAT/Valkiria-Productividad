# ADR-0007 · Empaquetado del backend como sidecar firmado (PyInstaller onedir)

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
- Valkiria Core se empaqueta con **PyInstaller en modo *onedir*** por plataforma y se declara como `externalBin` (sidecar) de Tauri.
- Se firma cada binario: Developer ID con *hardened runtime* y notarización en macOS, y Authenticode en Windows.
- Las herramientas Office se ejecutan con el mismo intérprete en un subproceso con límites de recursos.

## Alternativas
- **Nuitka:** binario más rápido, pero la compilación es más compleja y lenta; se reevalúa en F10.
- **uv con python-build-standalone sin congelar:** son miles de archivos que firmar y la superficie es mayor.
- **Contenedor:** no es viable en el escritorio.

## Consecuencias
- (+) Instalación sin Python del sistema; firma más simple.
- (−) Tamaño de entre 150 y 300 MB y posibles falsos positivos de antivirus (riesgo R-04, que se mitiga con firma y *onedir*).
