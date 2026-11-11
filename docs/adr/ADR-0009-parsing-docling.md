# ADR-0009 · Parsing de documentos con Docling

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
- **Docling** (MIT) para PDF, DOCX, PPTX, XLSX, HTML y MD, con estructura (títulos, tablas y páginas) preservada.
- `pypdfium2` como lector rápido de respaldo.
- **RapidOCR** (Apache 2.0) o el VLM (F8) para escaneos.
- Integración mediante `langchain-docling`.

## Consecuencias
- (+) Chunks con página y sección, que permiten citas precisas.
- (−) Docling es pesado y sus modelos de layout ocupan unos 0.5 GB; se cargan bajo demanda y el modo "rápido" usa solo `pypdfium2`.
