# Arranca la app Dash y expone un túnel público con Cloudflare
# Requisitos: tener cloudflared instalado y accesible en PATH
#   winget install Cloudflare.cloudflared
#   # o choco install cloudflared

param(
    [string]$Port = "8050",
    [string]$BindHost = "127.0.0.1",
    [string]$OCDSUrl = "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
)

$ErrorActionPreference = "Stop"

function Wait-Port {
    param(
        [Parameter(Mandatory=$true)][string]$Host,
        [Parameter(Mandatory=$true)][int]$Port,
        [int]$TimeoutSec = 90
    )
    for ($i = 0; $i -lt $TimeoutSec; $i++) {
        if (Test-NetConnection -ComputerName $Host -Port $Port -InformationLevel Quiet) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

Write-Host "[1/3] Activando venv si existe..."
if (Test-Path .\.venv\Scripts\Activate.ps1) {
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "No se encontró .venv. Puedes crear uno con: py -3 -m venv .venv"
}

Write-Host "[2/3] Exportando variables y ejecutando la app..."
$env:OCDS_JSON_URL = $OCDSUrl
$env:HOST = $BindHost
$env:PORT = $Port

# Arrancar la app en segundo plano con logs
$stdout = Join-Path $PSScriptRoot "app_stdout.log"
$stderr = Join-Path $PSScriptRoot "app_stderr.log"
if (Test-Path $stdout) { Remove-Item $stdout -Force }
if (Test-Path $stderr) { Remove-Item $stderr -Force }
$proc = Start-Process -FilePath "python" -ArgumentList "app\app.py" -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Minimized

# Esperar a que el puerto esté escuchando
if (-not (Wait-Port -Host $BindHost -Port [int]$Port -TimeoutSec 90)) {
    Write-Host "⚠️ La app no respondió en http://${BindHost}:${Port} dentro del tiempo de espera." -ForegroundColor Yellow
    if (Test-Path $stderr) {
        Write-Host "Últimas líneas de error:" -ForegroundColor Yellow
        Get-Content $stderr -Tail 40 | Write-Host
    }
    Write-Error "Abortando apertura del túnel. Revisa los logs: $stdout / $stderr"
}

Write-Host "[3/3] Abriendo túnel con Cloudflare (cloudflared)..."
# El túnel imprime una URL pública https://xxxx.trycloudflare.com
cloudflared tunnel --url "http://${BindHost}:${Port}"