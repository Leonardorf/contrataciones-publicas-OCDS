Uso
===

Para ejecutar la aplicación Dash en local, siga estos pasos: (Windows PowerShell)

1. Active su entorno virtual.
2. Desde PowerShell, ejecute:
```powershell
py -3 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install -r requirements.txt

# Dataset (opcional: por defecto usa una URL pública)
$env:OCDS_JSON_URL = "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
$env:PORT = "8050"

python app\app.py
```

Vea la aplicación en el navegador en la URL que se indique en la consola.

GitHub Codespaces

Al abrir el repositorio en Codespaces, el contenedor instala dependencias automáticamente.
Luego ejecuta:
```bash
export OCDS_JSON_URL="https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
export PORT=8050
python app/app.py
```
