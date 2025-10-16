Introducción
============

Este proyecto implementa un dashboard con Dash para explorar datos de
contrataciones públicas de la Provincia de Mendoza bajo el estándar OCDS.

La documentación describe el enfoque, componentes principales y guías de uso.


Novedades 0.1.10
-----------------

- Página "Insumos" con nuevos switches:
	- Medida: Monto (M) o Cantidad.
	- Vista: Agregado (Ítem) o Por licitante.
- Top 20 aplicado a tabla y gráfico según la selección.
- En "Por licitante", el orden del eje Y se basa en el total agregado del insumo (barras apiladas por licitante).
- Eje Y con todas las etiquetas visibles (altura y margen dinámicos).
- Etiqueta del eje Y cambiada a "Insumo".
- Valores por defecto: Monto + Por licitante.
