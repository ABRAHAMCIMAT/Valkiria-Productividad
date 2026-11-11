# ADR-0012 · Identidad local y gestión de secretos

**Estado:** Aceptada · **Fecha:** 2026-11-10 · **Revisión:** en cada cierre de fase

## Decisión
- Escritorio: **sin cuentas**. La identidad es el usuario del SO, que se registra en la auditoría.
- Secretos (API key de Jan, claves de conectores) en el **llavero del SO** con la librería `keyring`: Keychain en macOS y Credential Manager en Windows.
- El bearer de sesión solo vive en memoria.
- Cifrado en reposo delegado a FileVault o BitLocker; la app verifica que esté activo y avisa si no.
- Modo equipo: **Keycloak** (OIDC) y **OpenBao** para los secretos del servidor.

## Consecuencias
- (+) Elimina la dependencia de Entra ID; no hay credenciales en archivos.
- (−) Sin cifrado propio de la BD; se reevalúa SQLCipher si TI de VALTRE lo exige.
