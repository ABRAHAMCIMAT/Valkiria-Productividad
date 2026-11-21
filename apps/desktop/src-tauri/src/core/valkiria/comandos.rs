//! Comandos de Tauri del perfil de hardware (HU-04) y registro de `app.start` (RN-04.3).
use super::auditoria;
use super::perfil::{self, Acelerador, Gpu, Perfil, Recomendacion};
use crate::core::app::commands::get_jan_data_folder_path;
use serde::Serialize;
use serde_json::{json, Map, Value};
use std::fs;
use std::path::{Path, PathBuf};
use tauri::{AppHandle, Runtime};
use tauri_plugin_hardware::SystemInfo;

/// Carpeta de Valkiria dentro de la carpeta de datos de la app.
fn carpeta<R: Runtime>(app: &AppHandle<R>) -> PathBuf {
    get_jan_data_folder_path(app.clone()).join("valkiria")
}

pub fn ruta_auditoria(base: &Path) -> PathBuf {
    base.join("auditoria").join("audit.jsonl")
}

fn ruta_perfil(base: &Path) -> PathBuf {
    base.join("perfil.json")
}

/// Perfil que eligió el usuario, si eligió alguno.
pub fn perfil_elegido(base: &Path) -> Option<Perfil> {
    let texto = fs::read_to_string(ruta_perfil(base)).ok()?;
    serde_json::from_str::<Value>(&texto)
        .ok()?
        .get("perfil")
        .and_then(|p| serde_json::from_value(p.clone()).ok())
}

fn guardar_perfil(base: &Path, p: Perfil) -> Result<(), String> {
    fs::create_dir_all(base).map_err(|e| format!("no se pudo crear {}: {e}", base.display()))?;
    fs::write(ruta_perfil(base), json!({ "perfil": p }).to_string())
        .map_err(|e| format!("no se pudo guardar el perfil: {e}"))
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct OpcionPerfil {
    pub perfil: Perfil,
    pub disponible: bool,
    /// Por qué no está disponible (CA-04.2), o `None` si lo está.
    pub motivo: Option<String>,
}

/// Lo que muestra la pantalla de hardware: detección, perfil en uso, opciones y recomendación.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct EstadoPerfil {
    pub ram_gb: u64,
    pub so: String,
    pub arch: String,
    pub acelerador: Acelerador,
    pub perfil: Perfil,
    pub perfil_maximo: Perfil,
    pub aviso_rendimiento: bool,
    pub opciones: Vec<OpcionPerfil>,
    pub recomendacion: Recomendacion,
}

fn gpus(info: &SystemInfo) -> Vec<Gpu> {
    info.gpus
        .iter()
        .map(|g| Gpu {
            nombre: g.name.clone(),
            nvidia: g.nvidia_info.is_some(),
            vulkan: g.vulkan_info.is_some(),
        })
        .collect()
}

/// Estado del perfil para un equipo y una elección dados. No toca disco ni Tauri.
pub fn estado(info: &SystemInfo, arch: &str, elegido: Option<Perfil>) -> EstadoPerfil {
    let ram = perfil::ram_gb(info.total_memory);
    let actual = perfil::efectivo(elegido, ram);
    let catalogo = perfil::leer_catalogo(perfil::CATALOGO_YAML).unwrap_or_else(|e| {
        log::error!("Valkiria: {e}");
        Vec::new()
    });
    EstadoPerfil {
        ram_gb: ram,
        so: info.os_type.clone(),
        arch: arch.to_string(),
        acelerador: perfil::acelerador(&info.os_type, arch, &gpus(info)),
        perfil: actual,
        perfil_maximo: perfil::perfil_maximo(ram),
        aviso_rendimiento: perfil::aviso_rendimiento(ram),
        opciones: Perfil::TODOS
            .iter()
            .map(|&p| {
                let motivo = perfil::motivo_no_disponible(p, ram);
                OpcionPerfil {
                    perfil: p,
                    disponible: motivo.is_none(),
                    motivo,
                }
            })
            .collect(),
        recomendacion: perfil::recomendar(&catalogo, actual),
    }
}

/// Datos del evento `app.start` (RN-04.3): el perfil y el hardware detectado, sin datos personales
/// (ni usuario ni nombre del equipo).
pub fn datos_app_start(
    info: &SystemInfo,
    e: &EstadoPerfil,
    app_version: &str,
) -> Map<String, Value> {
    let gpus: Vec<&str> = info.gpus.iter().map(|g| g.name.as_str()).collect();
    let v = json!({
        "app_version": app_version,
        "so": e.so,
        "so_version": info.os_name,
        "arch": e.arch,
        "cpu": info.cpu.name,
        "ram_gb": e.ram_gb,
        "gpus": gpus,
        "acelerador": e.acelerador,
        "perfil": e.perfil,
        "perfil_maximo": e.perfil_maximo,
        "aviso_rendimiento": e.aviso_rendimiento,
    });
    v.as_object().cloned().unwrap_or_default()
}

fn ahora() -> String {
    chrono::Utc::now().to_rfc3339_opts(chrono::SecondsFormat::Millis, true)
}

/// Se llama en el `setup` de la app: verifica el log de auditoría y anexa `app.start`.
pub fn registrar_arranque<R: Runtime>(app: &AppHandle<R>, app_version: &str) {
    let base = carpeta(app);
    let info = tauri_plugin_hardware::get_system_info();
    let e = estado(&info, std::env::consts::ARCH, perfil_elegido(&base));
    match auditoria::anexar(
        &ruta_auditoria(&base),
        "app",
        "app.start",
        &ahora(),
        datos_app_start(&info, &e, app_version),
    ) {
        Ok(ev) => log::info!(
            "Valkiria: app.start #{} · perfil {:?} · {} GB · {:?}",
            ev["seq"],
            e.perfil,
            e.ram_gb,
            e.acelerador
        ),
        Err(err) => log::error!("Valkiria: no se pudo registrar app.start: {err}"),
    }
}

#[tauri::command]
pub fn valkiria_perfil_hardware<R: Runtime>(app: AppHandle<R>) -> EstadoPerfil {
    let info = tauri_plugin_hardware::get_system_info();
    estado(
        &info,
        std::env::consts::ARCH,
        perfil_elegido(&carpeta(&app)),
    )
}

/// RN-04.2: guarda el perfil si la RAM lo permite; si no, devuelve el motivo y no cambia nada.
#[tauri::command]
pub fn valkiria_elegir_perfil<R: Runtime>(
    app: AppHandle<R>,
    perfil: Perfil,
) -> Result<EstadoPerfil, String> {
    let info = tauri_plugin_hardware::get_system_info();
    let p = perfil::elegir(perfil, perfil::ram_gb(info.total_memory))?;
    let base = carpeta(&app);
    guardar_perfil(&base, p)?;
    Ok(estado(&info, std::env::consts::ARCH, Some(p)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tauri_plugin_hardware::{CpuStaticInfo, GpuInfo, Vendor};

    fn equipo(total_mib: u64, os: &str, gpus: Vec<GpuInfo>) -> SystemInfo {
        SystemInfo {
            cpu: CpuStaticInfo {
                name: "CPU de prueba".into(),
                core_count: 8,
                arch: "aarch64".into(),
                extensions: vec![],
            },
            os_type: os.into(),
            os_name: "SO 1.0".into(),
            total_memory: total_mib,
            gpus,
        }
    }

    #[test]
    fn test_ca_04_1_equipo_de_32_gb_con_metal_queda_en_avanzado() {
        let e = estado(&equipo(32 * 1024, "macos", vec![]), "aarch64", None);
        assert_eq!(e.perfil, Perfil::Avanzado);
        assert_eq!(e.acelerador, Acelerador::Metal);
        assert!(e.opciones.iter().all(|o| o.disponible));
        // El catálogo aún no trae modelo principal (lo elige el benchmark, incremento 1.5).
        assert!(e.recomendacion.router.is_some());
    }

    #[test]
    fn test_ca_04_2_en_16_gb_la_opcion_avanzado_esta_deshabilitada_con_su_motivo() {
        let e = estado(&equipo(16 * 1024, "windows", vec![]), "x86_64", None);
        assert_eq!(e.perfil, Perfil::Estandar);
        let avanzado = e
            .opciones
            .iter()
            .find(|o| o.perfil == Perfil::Avanzado)
            .unwrap();
        assert!(!avanzado.disponible);
        assert!(avanzado.motivo.as_deref().unwrap().contains("32 GB"));
        let estandar = e
            .opciones
            .iter()
            .find(|o| o.perfil == Perfil::Estandar)
            .unwrap();
        assert!(estandar.disponible && estandar.motivo.is_none());
    }

    #[test]
    fn test_ca_04_1_app_start_registra_perfil_y_hardware_sin_datos_personales() {
        let gpu = GpuInfo {
            name: "RTX 4070".into(),
            total_memory: 12 * 1024,
            vendor: Vendor::NVIDIA,
            uuid: "uuid".into(),
            driver_version: "1".into(),
            nvidia_info: None,
            vulkan_info: None,
        };
        let info = equipo(32 * 1024, "windows", vec![gpu]);
        let e = estado(&info, "x86_64", None);
        let datos = datos_app_start(&info, &e, "0.0.1");
        for campo in [
            "perfil",
            "perfil_maximo",
            "ram_gb",
            "acelerador",
            "so",
            "so_version",
            "arch",
            "cpu",
            "gpus",
            "app_version",
        ] {
            assert!(datos.contains_key(campo), "falta {campo}");
        }
        assert_eq!(datos["perfil"], "avanzado");
        assert_eq!(datos["gpus"], json!(["RTX 4070"]));
        let dir = tempfile::tempdir().unwrap();
        let ruta = ruta_auditoria(dir.path());
        let ev = auditoria::anexar(&ruta, "app", "app.start", "2026-11-20T10:00:00.000Z", datos)
            .unwrap();
        assert_eq!(ev["event"], "app.start");
        assert!(auditoria::verificar(&ruta).is_ok());
        let texto = fs::read_to_string(&ruta).unwrap();
        for prohibido in ["USER", "USERNAME", "hostname", "home"] {
            assert!(!texto.contains(prohibido), "{prohibido} en el log");
        }
    }

    #[test]
    fn la_eleccion_se_guarda_y_se_lee() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(perfil_elegido(dir.path()), None);
        guardar_perfil(dir.path(), Perfil::Estandar).unwrap();
        assert_eq!(perfil_elegido(dir.path()), Some(Perfil::Estandar));
        let e = estado(
            &equipo(64 * 1024, "macos", vec![]),
            "aarch64",
            perfil_elegido(dir.path()),
        );
        assert_eq!(e.perfil, Perfil::Estandar);
        assert_eq!(e.perfil_maximo, Perfil::Avanzado);
    }
}
