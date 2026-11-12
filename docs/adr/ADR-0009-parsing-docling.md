# ADR-0009 · Parsing de documentos con Docling

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
- **Docling** (MIT) para PDF, DOCX, PPTX, XLSX, HTML y MD, con estructura (títulos, tablas y páginas) preservada.
- `pypdfium2` como lector rápido de respaldo.
- **OCR de escaneos:** el VLM (F8) como vía principal y, de respaldo, el OCR del sistema operativo: Apple Vision (`ocrmac`) en macOS y Windows.Media.Ocr o tesserocr en Windows (se decide en F8).
- Integración con un **adaptador propio** en Core sobre `DocumentConverter`; el troceo lo hace `langchain-text-splitters`.

## Revisión 2026-11-12 (Python 3.15, R-11)
- Se instala **`docling-slim[convert-core,format-pdf,format-office,format-html,format-markdown,models-local]`**, más `feat-ocr-mac` en macOS. El paquete `docling` completo trae rapidocr, cuya dependencia pyclipper (C++) no publica *wheels* `cp315`.
- Se descarta **RapidOCR** como respaldo por pyclipper. Con su motor torch funcionó (3 de 3 frases), pero exige compilar pyclipper.
- Se descarta **`langchain-docling`** 3.0: trae `docling-slim[feat-chunking]`, cuya dependencia tree-sitter no publica `cp315`.
- Verificado en un Mac M4 con Python 3.15: el conjunto mínimo con ocrmac convirtió un PDF escaneado y reconoció 3 de 3 frases. Detalle en ADR-0002 (segunda revisión).

## Consecuencias
- (+) Chunks con página y sección, que permiten citas precisas.
- (−) Docling es pesado y sus modelos de layout ocupan unos 0.5 GB; se cargan bajo demanda y el modo "rápido" usa solo `pypdfium2`.
