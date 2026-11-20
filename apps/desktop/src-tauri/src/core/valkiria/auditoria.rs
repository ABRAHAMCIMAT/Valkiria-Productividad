//! Log de auditoría en tiempo de ejecución (docs/05 §4.3): JSONL de solo anexar, encadenado por hash.
//!
//! Cada línea es un evento con `seq`, `ts`, `actor`, `event`, sus datos, `prev_hash` y
//! `hash = SHA256(prev_hash + json_canonico(evento sin hash))`. El JSON canónico ordena las claves y
//! no lleva espacios, así que el hash no depende del orden en que se armó el evento. Alterar,
//! borrar o reordenar una línea rompe la cadena y [`verificar`] lo detecta.
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

/// `prev_hash` del primer evento.
pub const GENESIS: &str = "0000000000000000000000000000000000000000000000000000000000000000";

/// JSON sin espacios y con las claves de cada objeto ordenadas.
pub fn json_canonico(v: &Value) -> String {
    match v {
        Value::Object(m) => {
            let mut claves: Vec<&String> = m.keys().collect();
            claves.sort();
            let campos: Vec<String> = claves
                .into_iter()
                .map(|k| format!("{}:{}", Value::String(k.clone()), json_canonico(&m[k])))
                .collect();
            format!("{{{}}}", campos.join(","))
        }
        Value::Array(a) => {
            let elems: Vec<String> = a.iter().map(json_canonico).collect();
            format!("[{}]", elems.join(","))
        }
        otro => otro.to_string(),
    }
}

/// Hash de un evento: SHA-256 de `prev_hash` seguido del JSON canónico del evento sin `hash`.
pub fn hash_evento(prev_hash: &str, evento_sin_hash: &Value) -> String {
    let mut h = Sha256::new();
    h.update(prev_hash.as_bytes());
    h.update(json_canonico(evento_sin_hash).as_bytes());
    hex::encode(h.finalize())
}

/// Estado de la cadena: último `seq` y último `hash` (o [`GENESIS`] si el log está vacío).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Cola {
    pub seq: u64,
    pub hash: String,
}

/// Recorre el log y comprueba cada eslabón. Devuelve la cola, o la primera línea que no cuadra.
pub fn verificar(ruta: &Path) -> Result<Cola, String> {
    let mut cola = Cola {
        seq: 0,
        hash: GENESIS.to_string(),
    };
    let texto = match fs::read_to_string(ruta) {
        Ok(t) => t,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(cola),
        Err(e) => return Err(format!("no se pudo leer {}: {e}", ruta.display())),
    };
    for (i, linea) in texto
        .lines()
        .enumerate()
        .filter(|(_, l)| !l.trim().is_empty())
    {
        let n = i + 1;
        let mut ev: Map<String, Value> =
            serde_json::from_str(linea).map_err(|e| format!("línea {n}: no es JSON ({e})"))?;
        let hash = ev
            .remove("hash")
            .and_then(|h| h.as_str().map(str::to_owned))
            .ok_or_else(|| format!("línea {n}: sin hash"))?;
        let seq = ev.get("seq").and_then(Value::as_u64);
        if seq != Some(cola.seq + 1) {
            return Err(format!(
                "línea {n}: seq {seq:?}, se esperaba {}",
                cola.seq + 1
            ));
        }
        if ev.get("prev_hash").and_then(Value::as_str) != Some(cola.hash.as_str()) {
            return Err(format!(
                "línea {n}: prev_hash no enlaza con el evento anterior"
            ));
        }
        if hash_evento(&cola.hash, &Value::Object(ev)) != hash {
            return Err(format!("línea {n}: el hash no corresponde al contenido"));
        }
        cola = Cola {
            seq: cola.seq + 1,
            hash,
        };
    }
    Ok(cola)
}

/// Anexa un evento al final del log y lo devuelve tal como quedó escrito.
///
/// `datos` no debe traer `seq`, `ts`, `actor`, `event`, `prev_hash` ni `hash`: los pone esta función.
/// Si la cadena previa está rota, el evento se anexa igual (el log es de solo anexar y no se
/// reescribe) enlazado a la última línea legible, y `cadena_integra` queda en `false`.
pub fn anexar(
    ruta: &Path,
    actor: &str,
    evento: &str,
    ts: &str,
    datos: Map<String, Value>,
) -> Result<Value, String> {
    let (cola, integra) = match verificar(ruta) {
        Ok(c) => (c, true),
        Err(e) => {
            log::error!("Auditoría: la cadena de {} está rota: {e}", ruta.display());
            (ultima_legible(ruta), false)
        }
    };
    let mut ev = datos;
    ev.insert("seq".into(), Value::from(cola.seq + 1));
    ev.insert("ts".into(), Value::from(ts));
    ev.insert("actor".into(), Value::from(actor));
    ev.insert("event".into(), Value::from(evento));
    ev.insert("cadena_integra".into(), Value::from(integra));
    ev.insert("prev_hash".into(), Value::from(cola.hash.clone()));
    let mut ev = Value::Object(ev);
    let hash = hash_evento(&cola.hash, &ev);
    ev["hash"] = Value::from(hash);

    if let Some(dir) = ruta.parent() {
        fs::create_dir_all(dir).map_err(|e| format!("no se pudo crear {}: {e}", dir.display()))?;
    }
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(ruta)
        .map_err(|e| format!("no se pudo abrir {}: {e}", ruta.display()))?;
    writeln!(f, "{}", json_canonico(&ev)).map_err(|e| format!("no se pudo escribir: {e}"))?;
    f.sync_all()
        .map_err(|e| format!("no se pudo sincronizar: {e}"))?;
    Ok(ev)
}

/// Último `seq` y `hash` que se pueden leer, aunque la cadena no cuadre.
fn ultima_legible(ruta: &Path) -> Cola {
    fs::read_to_string(ruta)
        .ok()
        .and_then(|t| {
            t.lines().rev().find_map(|l| {
                let v: Value = serde_json::from_str(l).ok()?;
                Some(Cola {
                    seq: v.get("seq")?.as_u64()?,
                    hash: v.get("hash")?.as_str()?.to_owned(),
                })
            })
        })
        .unwrap_or(Cola {
            seq: 0,
            hash: GENESIS.to_string(),
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn datos(v: Value) -> Map<String, Value> {
        v.as_object().unwrap().clone()
    }

    #[test]
    fn el_json_canonico_ordena_claves_y_no_depende_del_orden_de_insercion() {
        let a = json!({"b": 1, "a": {"d": [1, {"z": true, "y": null}], "c": "ñ"}});
        assert_eq!(
            json_canonico(&a),
            r#"{"a":{"c":"ñ","d":[1,{"y":null,"z":true}]},"b":1}"#
        );
    }

    #[test]
    fn eventos_encadenados_se_verifican() {
        let dir = tempfile::tempdir().unwrap();
        let ruta = dir.path().join("auditoria").join("audit.jsonl");
        let e1 = anexar(
            &ruta,
            "app",
            "app.start",
            "2026-11-20T10:00:00.000Z",
            datos(json!({"perfil": "estandar"})),
        )
        .unwrap();
        let e2 = anexar(
            &ruta,
            "app",
            "app.start",
            "2026-11-20T11:00:00.000Z",
            Map::new(),
        )
        .unwrap();
        assert_eq!(e1["seq"], 1);
        assert_eq!(e1["prev_hash"], GENESIS);
        assert_eq!(e2["prev_hash"], e1["hash"]);
        assert_eq!(e2["cadena_integra"], true);
        let cola = verificar(&ruta).unwrap();
        assert_eq!(
            cola,
            Cola {
                seq: 2,
                hash: e2["hash"].as_str().unwrap().into()
            }
        );
    }

    #[test]
    fn alterar_una_linea_rompe_la_cadena_y_el_siguiente_evento_lo_marca() {
        let dir = tempfile::tempdir().unwrap();
        let ruta = dir.path().join("audit.jsonl");
        anexar(
            &ruta,
            "app",
            "app.start",
            "t1",
            datos(json!({"perfil": "estandar"})),
        )
        .unwrap();
        anexar(&ruta, "app", "app.start", "t2", Map::new()).unwrap();
        let texto = fs::read_to_string(&ruta)
            .unwrap()
            .replacen("estandar", "avanzado", 1);
        fs::write(&ruta, texto).unwrap();
        assert!(verificar(&ruta).unwrap_err().contains("línea 1"));

        let e3 = anexar(&ruta, "app", "app.start", "t3", Map::new()).unwrap();
        assert_eq!(e3["seq"], 3);
        assert_eq!(e3["cadena_integra"], false);
        assert_eq!(
            fs::read_to_string(&ruta).unwrap().lines().count(),
            3,
            "no se reescribe"
        );
    }

    #[test]
    fn borrar_una_linea_rompe_la_cadena() {
        let dir = tempfile::tempdir().unwrap();
        let ruta = dir.path().join("audit.jsonl");
        for t in ["t1", "t2", "t3"] {
            anexar(&ruta, "app", "app.start", t, Map::new()).unwrap();
        }
        let lineas: Vec<String> = fs::read_to_string(&ruta)
            .unwrap()
            .lines()
            .map(String::from)
            .collect();
        fs::write(&ruta, format!("{}\n{}\n", lineas[0], lineas[2])).unwrap();
        assert!(verificar(&ruta).unwrap_err().contains("línea 2"));
    }

    #[test]
    fn un_log_que_no_existe_es_una_cadena_vacia() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(
            verificar(&dir.path().join("no-existe.jsonl")).unwrap(),
            Cola {
                seq: 0,
                hash: GENESIS.into()
            }
        );
    }
}
