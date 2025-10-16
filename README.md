# Contrataciones Públicas de Mendoza (OCDS)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Leonardorf/contrataciones-publicas-OCDS?quickstart=1)

> Documentación del proyecto (GitHub Pages): https://leonardorf.github.io/contrataciones-publicas-OCDS/

**Autor:** Ing. Leonardo Raúl Federico Villegas  
Contacto: leonfevi@gmail.com · GitHub: https://github.com/Leonardorf

## Introducción
Este proyecto tiene como objetivo proporcionar una plataforma para analizar y visualizar datos de contrataciones públicas de la Provincia de Mendoza, utilizando el estándar OCDS (Open Contracting Data Standard).


## Librerías Utilizadas
En este proyecto se han utilizado diversas librerías de Python que son fundamentales en el ámbito de la ciencia de datos y el desarrollo de aplicaciones:

- **Pandas**: Para la manipulación y análisis de datos estructurados. Permite realizar operaciones como limpieza, transformación y agregación de datos de manera eficiente.
- **Plotly**: Para la creación de gráficos interactivos que facilitan la visualización de datos complejos.
- **Dash**: Para el desarrollo de aplicaciones web interactivas orientadas a la visualización de datos.
- **NumPy**: Para operaciones matemáticas y manejo de arreglos multidimensionales.
- **Sphinx**: Para la generación de documentación técnica del proyecto.

Estas herramientas son esenciales en la ciencia de datos, ya que permiten transformar datos en información útil y comprensible para la toma de decisiones.

## Estandar OCDS
El estándar OCDS (Open Contracting Data Standard) es un marco global para la publicación de datos de contrataciones públicas. El uso del estándar OCDS asegura que los datos sean accesibles, comprensibles y reutilizables por diferentes audiencias. Su importancia radica en:

- **Transparencia**: Facilita el acceso a información clara y estructurada sobre los procesos de contratación pública.
- **Comparabilidad**: Permite comparar datos entre diferentes jurisdicciones y períodos de tiempo.
- **Análisis**: Proporciona un formato uniforme que facilita el análisis y la auditoría de los datos.
- **Impacto social**: Promueve la rendición de cuentas y la lucha contra la corrupción en los procesos de contratación pública.


## Se emplean las siguientes técnicas para asegurar el rigor metodológico:

- **Validación de datos**: Uso de la librería Pandas para detectar y manejar valores nulos o inconsistentes.
- **Transformación de datos**: Limpieza y normalización de los datos gracias al uso de formato OCDS.
- **Fuentes confiables**: Los datos provienen de sistemas oficiales como el sistema COMPRAR del Gobierno de Mendoza.

## El proyecto tiene un impacto significativo en diversas áreas:

- **Gobierno**: Mejora la transparencia y facilita la rendición de cuentas.
- **Ciudadanos**: Permite a los ciudadanos entender cómo se utilizan los recursos públicos, promover los proyectos sobre presupuesto participativo.
- **Investigadores /ONGs**: Proporciona un conjunto de datos estructurados para análisis avanzados.

## Casos de uso:
  - Identificación de patrones de gasto público.
  - Evaluación de la eficiencia en las contrataciones.
  - Comparación de datos entre diferentes períodos.
 
## La plataforma está diseñada para simplificar datos complejos mediante:

- **Gráficos interactivos**: Uso de `Plotly` para explorar los datos de manera visual e intuitiva.
- **Interfaz amigable**: Desarrollo con Dash y Bootstrap para garantizar una experiencia de usuario fluida.
- **Síntesis de información**: Resúmenes claros y gráficos que destacan los puntos clave.


## El proyecto se distingue por:

- **Uso innovador de tecnologías**: Integración de Dash, Plotly y el estándar OCDS.
- **Enfoque único**: Combinación de análisis de datos con visualizaciones interactivas.
- **Adaptabilidad**: La plataforma puede ser utilizada por diferentes audiencias con necesidades específicas.


## El diseño visual del proyecto se centra en:

- **Estética moderna**: Uso de Dash y Bootstrap para una interfaz atractiva y responsiva.
- **Gráficos de alta calidad**: Generación de visualizaciones claras y profesionales con `Plotly`.

## Ejemplo de gráficos:
- Gráficos de barras para comparar montos entre diferentes licitantes.
- Gráficos de líneas para mostrar la evolución mensual de los gastos.
- Diagramas circulares para representar la distribución de tipos de contratación.
  

## Novedades 0.1.10

- Página "Insumos" con switches de Medida (Monto/Cantidad) y Vista (Agregado/Por licitante).
- Top 20 aplicado a tabla y gráfico según la selección.
- En "Por licitante", el orden del eje Y se basa en el total agregado del insumo (barras apiladas por licitante).
- Eje Y con todas las etiquetas visibles (altura y margen dinámicos).
- Etiqueta del eje Y cambiada a "Insumo".
- Valores por defecto: Monto + Por licitante.


## Información Adicional
- Para más información sobre el estándar OCDS, visite: [Open Contracting Partnership](https://www.open-contracting.org/).
- Para detalles sobre el sistema Comprar- Mendoza : [Comprar- Mendoza](https://comprar.mendoza.gov.ar/).

## Cómo ejecutar la app (rápido)

### Local (Windows PowerShell)
```powershell
py -3 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install -r requirements.txt

# Dataset (opcional: por defecto usa una URL pública)
$env:OCDS_JSON_URL = "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
$env:PORT = "8050"

python app\app.py
```

## Demo pública temporal (Cloudflare Quick Tunnel)

Si querés compartir la app con alguien sin que tenga que instalar nada, podés abrir un túnel público temporal.

Opción 1: usar el script incluido (recomendado en Windows PowerShell)

1. Instalar cloudflared (una vez):
  - Con winget: `winget install Cloudflare.cloudflared`
  - Con Chocolatey: `choco install cloudflared`
2. Desde la carpeta del repo, ejecutá:
  - `scripts/start-cloudflared.ps1`

El script:
- Activa el venv si existe.
- Exporta `OCDS_JSON_URL`, `HOST` y `PORT`.
- Arranca la app en segundo plano.
- Abre un túnel y muestra en consola una URL pública del estilo `https://xxxx.trycloudflare.com` para compartir.

Parámetros opcionales del script:

```
scripts/start-cloudflared.ps1 -Port 8050 -Host 127.0.0.1 -OCDSUrl "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
```

Opción 2: hacerlo manualmente

1. Lanzá la app local
2. En otra terminal, ejecutá:

```
cloudflared tunnel --url http://localhost:8050
```

Mantené la consola abierta; si la cerrás, el enlace deja de funcionar. Cada vez que inicies el túnel obtendrás un enlace distinto (efímero).
### GitHub Codespaces
Al abrir el repositorio en Codespaces, el contenedor instala dependencias automáticamente.
Luego ejecuta:
```bash
export OCDS_JSON_URL="https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
export PORT=8050
python app/app.py
```

### Producción (Gunicorn)
```bash
gunicorn app.app:server --bind 0.0.0.0:${PORT:-8050}
```

La app escucha en 0.0.0.0 y lee HOST/PORT del entorno si están definidos.

## Despliegues gratuitos / PaaS sugeridos

### Opción A: Render (free tier) con `render.yaml`
Ya se incluye un archivo `render.yaml` que permite desplegar con "Blueprint Deploy" (Infrastructure as Code).

Pasos:
1. Crea cuenta en https://render.com/
2. En el dashboard: New + Blueprint → pega la URL del repo (`https://github.com/Leonardorf/contrataciones-publicas-OCDS`).
3. Revisa que el servicio aparezca con nombre `ocds-mendoza-dashboard`.
4. Ajusta (si quieres) la variable de entorno `OCDS_JSON_URL` (está marcada como `sync: false` para que la definas desde la UI si deseas cambiar la URL por defecto).
5. Lanza el deploy. Render instalará dependencias y ejecutará Gunicorn con el comando definido.
6. El health check usará automáticamente `/health`.

Si prefieres el flujo manual (sin blueprint):
1. New + Web Service → conecta tu repositorio.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `gunicorn app.app:server --bind 0.0.0.0:$PORT --workers=2 --timeout=120`
4. Añade variable `OCDS_JSON_URL` si querés override del dataset.
5. (Opcional) Configura Health Check Path = `/health`.

### Opción B: Railway
1. Crea cuenta en https://railway.app/
2. Nuevo proyecto desde repo GitHub.
3. Variables: `PORT=8080` (Railway suele inyectar una), ajusta Start Command:
  ```
  gunicorn app.app:server --bind 0.0.0.0:$PORT
  ```
4. Si el puerto asignado cambia, Railway lo expone como variable (mantenlo con $PORT).

### Opción C: Deta Space (micro)
1. Empaqueta con `Procfile` (Deta detecta Python usando `main.py` normalmente; aquí usar contenedor si cambian políticas).
2. Alternativa: usar Dockerfile (Beta) subiendo la imagen.

### Opción D: Hugging Face Spaces (Docker)
1. Crear un Space → Tipo: Docker.
2. Sube `Dockerfile` y `requirements.txt` (ya presentes) y carpeta `app/`.
3. Define variable `PORT=7860` (HF usa 7860 por defecto) y cambia CMD si deseas:
  ```Dockerfile
  CMD ["gunicorn", "app.app:server", "--bind", "0.0.0.0:7860", "--workers", "2", "--timeout", "120"]
  ```
4. Al construir, obtienes URL estable del Space.

### Variables útiles
| Nombre | Significado |
|--------|-------------|
| OCDS_JSON_URL | URL o ruta al JSON OCDS a cargar |
| PORT | Puerto de escucha (aportado por el PaaS) |
| HOST | Host binding (0.0.0.0 en producción) |

### Health Check
La ruta `/health` ya está implementada y devuelve JSON con `status`, `rows` y `sphinx_build`. Configura tu PaaS para usarla como verificación de estado.

## Gestión de Carga de Datos y Endpoints

La aplicación implementa un mecanismo resiliente de carga del dataset OCDS con soporte para:

- Carga inmediata por defecto (a menos que se active modo lazy).
- Sanitización automática de la URL (elimina comillas y espacios accidentales).
- Reintentos exponenciales (3 intentos) en caso de fallo temporal de red.
- Recarga manual vía endpoint `/reload-data` o botón en la UI.
- Evita cargar datos durante el build de documentación Sphinx (`SPHINX_BUILD=1`).

### Variables de entorno relevantes
| Variable | Uso | Valor por defecto | Notas |
|----------|-----|-------------------|-------|
| `OCDS_JSON_URL` | URL (o ruta local) al JSON OCDS a consumir | URL pública fija | Si está vacía o no definida se usa la URL por defecto. No pongas comillas alrededor. |
| `LAZY_LOAD` | Si `1`, difiere la carga hasta que un usuario lo solicite | `0` | En modo lazy el primer acceso que necesite datos o el botón de recarga dispara la carga. |
| `SPHINX_BUILD` | Si `1`, desactiva la carga real (solo docs) | `0` | No usar en producción. |

### Endpoint `/health`
Devuelve un JSON rápido, sin forzar (re)carga de datos:

Ejemplo respuesta (con datos cargados):
```json
{
  "status": "ok",
  "rows": 12456,
  "sphinx_build": false
}
```

PowerShell:
```powershell
Invoke-RestMethod -Uri "https://TU-DOMINIO/health"
```

curl:
```bash
curl -s https://TU-DOMINIO/health | jq
```

Interpretación rápida:
- `rows = 0` puede indicar: carga en curso, modo lazy, fallo previo o dataset realmente vacío.
- `sphinx_build = true` significa que la app fue importada sólo para generar documentación (ignorar `rows`).

### Endpoint `/reload-data`
Fuerza un intento de recarga (omite cache si ya había datos). Útil tras corregir `OCDS_JSON_URL`.

PowerShell:
```powershell
Invoke-RestMethod -Uri "https://TU-DOMINIO/reload-data"
```

curl:
```bash
curl -s https://TU-DOMINIO/reload-data | jq
```

Respuesta esperada (éxito):
```json
{ "status": "ok", "rows": 12456 }
```

Si falla:
```json
{ "status": "error", "error": "Detalle del problema" }
```

### Botón "Forzar recarga de datos" en la interfaz
Cuando el DataFrame está vacío (por ejemplo al inicio con `LAZY_LOAD=1` o tras un fallo), la página Home muestra:

1. Mensaje: *"No hay datos disponibles (dataset vacío o carga diferida)."*
2. Botón: *Forzar recarga de datos*.
3. Un pequeño poller (`dcc.Interval`) que intenta detectar si tras la recarga ya hay filas.

Al completarse la carga, se informa la cantidad de filas y podés cambiar el año o refrescar el navegador para ver los gráficos.

### Flujo recomendado de verificación (troubleshooting)
1. Consultar `/health`.
   - Si `rows > 0`: OK.
2. Si `rows = 0`, invocar `/reload-data` o usar el botón.
3. Volver a consultar `/health`.
4. Si sigue en 0:
   - Verificar que la URL en `OCDS_JSON_URL` es accesible directamente (abrir en navegador / curl).
   - Quitar comillas envolventes en la variable (ej: usar `https://...json` y NO `"https://...json"`).
   - Revisar logs del servicio (Render / container) buscando líneas con `Fallo definitivo`.
5. (Opcional) Activar temporalmente `LAZY_LOAD=1` para que el arranque sea más rápido y luego forzar la carga manual.

### Ejemplo completo (PowerShell) cambiando la URL de datos
```powershell
$env:OCDS_JSON_URL = "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
python app\app.py

# En otra ventana, probar health y recarga
Invoke-RestMethod -Uri "http://localhost:8050/health"
Invoke-RestMethod -Uri "http://localhost:8050/reload-data"
```

### Script de smoke test rápido (opcional)
Guarda como `scripts/smoke.ps1` para verificar despliegue:
```powershell
param(
  [string]$Base = "http://localhost:8050"
)
$h = Invoke-RestMethod -Uri "$Base/health"
if($h.status -ne 'ok') { Write-Error "Health no OK"; exit 1 }
if($h.rows -eq 0) {
  Write-Host "Rows=0 → forzando recarga" -ForegroundColor Yellow
  $r = Invoke-RestMethod -Uri "$Base/reload-data"
  Start-Sleep -Seconds 3
  $h2 = Invoke-RestMethod -Uri "$Base/health"
  if($h2.rows -eq 0) { Write-Error "Sigue sin datos"; exit 2 }
}
Write-Host "Smoke test OK" -ForegroundColor Green
```

Con esto disponés de un camino claro para validar y recuperar la carga de datos tanto local como en producción.

### Consejos de optimización
- Evita cargar datasets enormes al iniciar: podrías pasar a lazy load.
- Usa `workers=2` en gunicorn para mantener consumo bajo.
- Agrega caché simple (por ejemplo functools.lru_cache) si repites transformaciones.

### Contenedor local (prueba)
```bash
docker build -t ocds-mza .
docker run -p 8050:8050 -e PORT=8050 ocds-mza
```
