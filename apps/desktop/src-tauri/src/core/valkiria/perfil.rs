//! Perfil de hardware (HU-04): reglas puras, sin Tauri, para probarlas con cualquier equipo simulado.
//!
//! - RN-04.1: menos de 16 GB de RAM → Estándar con aviso de rendimiento limitado; de 16 a 31 GB →
//!   Estándar; 32 GB o más → Avanzado.
//! - RN-04.2: el usuario puede bajar de perfil, pero no subir por encima de lo que permite su RAM.
use serde::{Deserialize, Serialize};

/// GB a partir de los cuales el perfil máximo es Avanzado.
pub const GB_AVANZADO: u64 = 32;
/// Por debajo de estos GB se avisa que el rendimiento será limitado.
pub const GB_AVISO: u64 = 16;

/// Catálogo de modelos aprobados (HU-05), el mismo que usan llmops y la prueba de humo del motor.
pub const CATALOGO_YAML: &str = include_str!("../../../../../../llmops/models/catalog.yaml");

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Perfil {
    Estandar,
    Avanzado,
}

impl Perfil {
    pub const TODOS: [Perfil; 2] = [Perfil::Estandar, Perfil::Avanzado];

    /// RAM mínima del perfil, en GB.
    pub fn ram_minima_gb(self) -> u64 {
        match self {
            Perfil::Estandar => 0,
            Perfil::Avanzado => GB_AVANZADO,
        }
    }

    pub fn nombre(self) -> &'static str {
        match self {
            Perfil::Estandar => "Estándar",
            Perfil::Avanzado => "Avanzado",
        }
    }
}

/// Backend de aceleración con el que corre el motor llama.cpp empaquetado.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Acelerador {
    Metal,
    Cuda,
    Vulkan,
    Cpu,
}

/// Lo que la detección necesita de una GPU, sacado de `tauri_plugin_hardware::GpuInfo`.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Gpu {
    pub nombre: String,
    pub nvidia: bool,
    pub vulkan: bool,
}

/// RAM total en GB enteros a partir de MiB. Se redondea porque el SO reporta menos que lo instalado
/// (Windows da unos 31,8 GiB en un equipo de 32 GB), y truncar dejaría ese equipo en Estándar.
pub fn ram_gb(total_mib: u64) -> u64 {
    (total_mib + 512) / 1024
}

/// RN-04.1: el perfil más alto que permite la RAM.
pub fn perfil_maximo(ram_gb: u64) -> Perfil {
    if ram_gb >= GB_AVANZADO {
        Perfil::Avanzado
    } else {
        Perfil::Estandar
    }
}

/// RN-04.1: con menos de 16 GB el perfil es Estándar pero se avisa del rendimiento limitado.
pub fn aviso_rendimiento(ram_gb: u64) -> bool {
    ram_gb < GB_AVISO
}

/// Backend que usará el motor: Metal en Apple Silicon; CUDA si hay una GPU NVIDIA; Vulkan si hay
/// otra GPU con Vulkan; si no, CPU. Es el mismo orden de preferencia de la variante cuda13-vulkan.
pub fn acelerador(so: &str, arch: &str, gpus: &[Gpu]) -> Acelerador {
    if so == "macos" && arch == "aarch64" {
        Acelerador::Metal
    } else if gpus.iter().any(|g| g.nvidia) {
        Acelerador::Cuda
    } else if gpus.iter().any(|g| g.vulkan) {
        Acelerador::Vulkan
    } else {
        Acelerador::Cpu
    }
}

/// Explicación de por qué un perfil no está disponible en este equipo.
pub fn motivo_no_disponible(perfil: Perfil, ram_gb: u64) -> Option<String> {
    (perfil > perfil_maximo(ram_gb)).then(|| {
        format!(
            "El perfil {} requiere {} GB de RAM o más; este equipo tiene {} GB.",
            perfil.nombre(),
            perfil.ram_minima_gb(),
            ram_gb
        )
    })
}

/// RN-04.2: acepta bajar de perfil y rechaza subir por encima de lo que permite la RAM.
pub fn elegir(solicitado: Perfil, ram_gb: u64) -> Result<Perfil, String> {
    match motivo_no_disponible(solicitado, ram_gb) {
        Some(motivo) => Err(motivo),
        None => Ok(solicitado),
    }
}

/// Perfil en uso: el que eligió el usuario, o el máximo si no eligió. Si la RAM bajó desde la
/// elección (otro equipo con la misma carpeta de datos), se limita al máximo actual.
pub fn efectivo(elegido: Option<Perfil>, ram_gb: u64) -> Perfil {
    let maximo = perfil_maximo(ram_gb);
    elegido.map_or(maximo, |p| p.min(maximo))
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ModeloCatalogo {
    pub id: String,
    #[serde(default)]
    pub nombre: String,
    #[serde(default)]
    pub rol: String,
    #[serde(default)]
    pub perfiles: Vec<Perfil>,
    #[serde(default)]
    pub ram_gb: f64,
}

#[derive(Deserialize)]
struct Catalogo {
    #[serde(default)]
    modelos: Vec<ModeloCatalogo>,
}

pub fn leer_catalogo(yaml: &str) -> Result<Vec<ModeloCatalogo>, String> {
    serde_yaml::from_str::<Catalogo>(yaml)
        .map(|c| c.modelos)
        .map_err(|e| format!("catálogo no válido: {e}"))
}

#[derive(Clone, Debug, Default, PartialEq, Serialize)]
pub struct Recomendacion {
    /// Modelo principal del perfil. `None` hasta que el benchmark lo elija (incremento 1.5).
    pub principal: Option<ModeloCatalogo>,
    pub router: Option<ModeloCatalogo>,
}

/// Modelos del catálogo recomendados para el perfil: el primero de cada rol que lo admite.
pub fn recomendar(catalogo: &[ModeloCatalogo], perfil: Perfil) -> Recomendacion {
    let del_rol = |rol: &str| {
        catalogo
            .iter()
            .find(|m| m.rol == rol && m.perfiles.contains(&perfil))
            .cloned()
    };
    Recomendacion {
        principal: del_rol("principal"),
        router: del_rol("router"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MIB_POR_GB: u64 = 1024;

    fn catalogo_con_principales() -> Vec<ModeloCatalogo> {
        leer_catalogo(
            r#"
modelos:
  - {id: chico, rol: principal, perfiles: [estandar]}
  - {id: grande, rol: principal, perfiles: [avanzado]}
  - {id: router, rol: router, perfiles: [estandar, avanzado]}
"#,
        )
        .unwrap()
    }

    #[test]
    fn test_ca_04_1_equipo_de_32_gb_con_metal_es_avanzado_y_recomienda_su_principal() {
        let ram = ram_gb(32 * MIB_POR_GB);
        assert_eq!(acelerador("macos", "aarch64", &[]), Acelerador::Metal);
        assert_eq!(perfil_maximo(ram), Perfil::Avanzado);
        let perfil = efectivo(None, ram);
        assert_eq!(perfil, Perfil::Avanzado);
        let rec = recomendar(&catalogo_con_principales(), perfil);
        assert_eq!(rec.principal.unwrap().id, "grande");
        assert_eq!(rec.router.unwrap().id, "router");
    }

    #[test]
    fn test_ca_04_1_equipo_de_32_gb_con_cuda_es_avanzado_aunque_windows_reporte_menos() {
        // Windows reserva memoria: un equipo de 32 GB reporta unos 32 560 MiB (31,8 GiB).
        let ram = ram_gb(32_560);
        let gpus = [Gpu {
            nombre: "RTX 4070".into(),
            nvidia: true,
            vulkan: true,
        }];
        assert_eq!(acelerador("windows", "x86_64", &gpus), Acelerador::Cuda);
        assert_eq!(efectivo(None, ram), Perfil::Avanzado);
    }

    #[test]
    fn test_ca_04_2_en_16_gb_avanzado_no_se_puede_elegir_y_explica_el_requisito() {
        let ram = ram_gb(16 * MIB_POR_GB);
        let err = elegir(Perfil::Avanzado, ram).unwrap_err();
        assert!(err.contains("32 GB"), "{err}");
        assert!(err.contains("16 GB"), "{err}");
        assert_eq!(efectivo(None, ram), Perfil::Estandar);
    }

    #[test]
    fn test_ca_04_2_bajar_de_perfil_si_se_permite() {
        let ram = ram_gb(64 * MIB_POR_GB);
        assert_eq!(elegir(Perfil::Estandar, ram), Ok(Perfil::Estandar));
        assert_eq!(efectivo(Some(Perfil::Estandar), ram), Perfil::Estandar);
        assert_eq!(motivo_no_disponible(Perfil::Avanzado, ram), None);
    }

    #[test]
    fn rn_04_1_umbrales_y_aviso() {
        for (gb, perfil, aviso) in [
            (8, Perfil::Estandar, true),
            (15, Perfil::Estandar, true),
            (16, Perfil::Estandar, false),
            (31, Perfil::Estandar, false),
            (32, Perfil::Avanzado, false),
            (128, Perfil::Avanzado, false),
        ] {
            assert_eq!(perfil_maximo(gb), perfil, "{gb} GB");
            assert_eq!(aviso_rendimiento(gb), aviso, "{gb} GB");
        }
    }

    #[test]
    fn una_eleccion_vieja_se_limita_a_la_ram_actual() {
        assert_eq!(efectivo(Some(Perfil::Avanzado), 16), Perfil::Estandar);
    }

    #[test]
    fn acelerador_vulkan_y_cpu() {
        let amd = [Gpu {
            nombre: "Radeon".into(),
            nvidia: false,
            vulkan: true,
        }];
        assert_eq!(acelerador("windows", "x86_64", &amd), Acelerador::Vulkan);
        assert_eq!(acelerador("windows", "x86_64", &[]), Acelerador::Cpu);
        assert_eq!(acelerador("macos", "x86_64", &[]), Acelerador::Cpu);
    }

    #[test]
    fn el_catalogo_empaquetado_se_lee_y_da_el_router_a_ambos_perfiles() {
        let catalogo = leer_catalogo(CATALOGO_YAML).unwrap();
        assert!(!catalogo.is_empty());
        for perfil in Perfil::TODOS {
            assert!(recomendar(&catalogo, perfil).router.is_some(), "{perfil:?}");
        }
    }

    #[test]
    fn un_catalogo_roto_es_un_error() {
        assert!(leer_catalogo("modelos: [{rol: principal}]").is_err());
    }
}
