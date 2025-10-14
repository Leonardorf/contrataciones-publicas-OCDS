# Arranca la app Dash y expone un túnel público con Cloudflare
# Requisitos: tener cloudflared instalado y accesible en PATH
#   winget install Cloudflare.cloudflared
#   # o choco install cloudflared

param(
    [string]$Port = "8050",
    [string]$Host = "127.0.0.1",
    [string]$OCDSUrl = "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Activando venv si existe..."
if (Test-Path .\.venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "No se encontró .venv. Puedes crear uno con: py -3 -m venv .venv"
}

Write-Host "[2/3] Exportando variables y ejecutando la app..."
$env:OCDS_JSON_URL = $OCDSUrl
$env:HOST = $Host
$env:PORT = $Port

# Arrancar la app en segundo plano
Start-Process -FilePath "python" -ArgumentList "app\app.py" -WindowStyle Minimized
Start-Sleep -Seconds 3

Write-Host "[3/3] Abriendo túnel con Cloudflare (cloudflared)..."
# El túnel imprime una URL pública https://xxxx.trycloudflare.com
cloudflared tunnel --url http://$Host:$Port