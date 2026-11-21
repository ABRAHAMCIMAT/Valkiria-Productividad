//! Código propio de Valkiria Productividad dentro del fork de Jan (no viene de upstream).
//!
//! F1, incremento 1.2 · HU-04 «Detección del perfil de hardware»:
//! - [`perfil`]: reglas RN-04.1 y RN-04.2 y la recomendación del catálogo, sin dependencias de Tauri.
//! - [`auditoria`]: log de auditoría JSONL encadenado por hash (docs/05 §4.3), con `app.start` (RN-04.3).
//! - [`comandos`]: comandos de Tauri para la interfaz y el registro del arranque.
//!
//! Los enganches con el código de Jan (`core/mod.rs`, `lib.rs` y la pantalla de hardware) los aplica
//! `tools/desktop/rebrand.py`, igual que el resto de desviaciones del fork.
pub mod auditoria;
pub mod comandos;
pub mod perfil;
