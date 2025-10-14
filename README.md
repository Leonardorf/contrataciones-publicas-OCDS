# Contrataciones Públicas de Mendoza (OCDS)

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Leonardorf/contrataciones-publicas-OCDS?quickstart=1)

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
