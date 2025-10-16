param(
    [int]$Port = 8050,
    [switch]$Lazy
)

Write-Host "==> Reiniciando app en puerto $Port..." -ForegroundColor Cyan

# 1) Ir a raíz del proyecto (scripts/..)
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

# 2) Si hay proceso escuchando en el puerto, terminarlo
try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
} catch {
    $conn = $null
}
if ($conn) {
    $owningPid = $conn.OwningProcess
    try {
        $p = Get-Process -Id $owningPid -ErrorAction Stop
        Write-Host "   - Matando proceso PID=$owningPid ($($p.ProcessName)) que usa el puerto $Port" -ForegroundColor Yellow
        Stop-Process -Id $owningPid -Force
        Start-Sleep -Milliseconds 300
    } catch {
        Write-Host "   - No se pudo obtener proceso para PID=$owningPid; continuando" -ForegroundColor DarkYellow
    }
}

# 3) Activar venv
$venvActivate = Join-Path $root ".venv/Scripts/Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "   - Activando entorno virtual (.venv)" -ForegroundColor Green
    & $venvActivate
} else {
    Write-Host "ERROR: No se encontró $venvActivate. Crea el venv o ajusta la ruta." -ForegroundColor Red
    exit 1
}

# 4) Flags de entorno
if ($Lazy -or ($env:LAZY_LOAD -eq '1')) {
    $env:LAZY_LOAD = '1'
    Write-Host "   - LAZY_LOAD=1 (carga diferida de datos)" -ForegroundColor Yellow
} else {
    Write-Host "   - LAZY_LOAD desactivado (carga completa al iniciar)" -ForegroundColor DarkYellow
}

# 5) Levantar la app
Write-Host "   - Iniciando: python app/app.py" -ForegroundColor Green
python app/app.py
