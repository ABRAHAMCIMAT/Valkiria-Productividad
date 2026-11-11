# Analiza el árbol de trabajo actual contra el SonarQube local (Windows / PowerShell 7).
# Requiere Docker Desktop y Git for Windows (usa bash para tools/sonar/sources.sh).
# Token: $env:SONAR_LOCAL_TOKEN, o en el Administrador de credenciales con el módulo
#   CredentialManager:  New-StoredCredential -Target valkiria-sonar-local -UserName sonar -Password <token>
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path "$PSScriptRoot/../..").Path
$Key = if ($env:SONAR_LOCAL_PROJECT_KEY) { $env:SONAR_LOCAL_PROJECT_KEY } else { 'valkiria-productividad' }
$ScannerImage = 'sonarsource/sonar-scanner-cli:12.2'

$Token = $env:SONAR_LOCAL_TOKEN
if (-not $Token -and (Get-Command Get-StoredCredential -ErrorAction SilentlyContinue)) {
  $Token = (Get-StoredCredential -Target valkiria-sonar-local).GetNetworkCredential().Password
}
if (-not $Token) { throw 'Define SONAR_LOCAL_TOKEN o guárdalo en el Administrador de credenciales.' }

$vars = @{}
bash "$Root/tools/sonar/sources.sh" | ForEach-Object { $k, $v = $_ -split '=', 2; $vars[$k] = $v }
if ($vars.has_code -ne 'true') { Write-Host 'Todavía no hay código propio que analizar.'; exit 0 }

$scanArgs = @("-Dsonar.projectKey=$Key", '-Dsonar.host.url=http://sonarqube:9000', "-Dsonar.sources=$($vars.sources)")
if ($vars.tests) { $scanArgs += "-Dsonar.tests=$($vars.tests)" }

docker run --rm --network valkiria-sonar_default -e "SONAR_TOKEN=$Token" -v "${Root}:/usr/src" -w /usr/src $ScannerImage @scanArgs
Write-Host "Resultados: http://127.0.0.1:9000/dashboard?id=$Key"
