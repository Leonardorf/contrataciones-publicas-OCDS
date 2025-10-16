Uso
===

Para ejecutar la aplicación Dash en local (Windows PowerShell):

1. Cree y active un entorno virtual.
2. Instale dependencias y ejecute la app.

Comandos en PowerShell:

.. code-block:: powershell

	py -3 -m venv .venv
	& ".\.venv\Scripts\Activate.ps1"
	python -m pip install -r requirements.txt

	# Dataset (opcional: por defecto usa una URL pública)
	$env:OCDS_JSON_URL = "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
	$env:PORT = "8050"

	python app\app.py

Vea la aplicación en el navegador en la URL que se indique en la consola.

GitHub Codespaces
-----------------

Al abrir el repositorio en Codespaces, el contenedor instala dependencias automáticamente.
Luego ejecute:

.. code-block:: bash

	export OCDS_JSON_URL="https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
	export PORT=8050
	python app/app.py


Insumos (métricas y vistas) — v0.1.10
-------------------------------------

La página "Insumos" incorpora controles para cambiar la métrica y la vista del Top 20:

- Medida:
	- "Monto (M)": suma en millones por insumo (etiquetas con sufijo M).
	- "Cantidad": suma de `quantity` por insumo (si está disponible), como entero.
- Vista:
	- "Agregado (Ítem)": suma por insumo (Código + Descripción).
	- "Por licitante": desagrega el insumo por licitante (barras apiladas por color).

Notas:
- El ranking muestra siempre el Top 20 según la selección.
- En la vista "Por licitante", el orden de los insumos se define por el total agregado del insumo.
- El eje Y mantiene visibles todas las etiquetas (altura y márgenes dinámicos).
- La etiqueta del eje Y es "Insumo".
