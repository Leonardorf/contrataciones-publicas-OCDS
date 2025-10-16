# Changelog

## [0.1.10] - 2025-10-16

### Cambios
- Insumos: agregados switches de Medida (Monto/Cantidad) y Vista (Agregado/Por licitante).
- Insumos: Top 20 por selección (tabla y gráfico), con formateos adecuados por métrica.
- Insumos: en vista “detalle”, el orden se basa en el total agregado del insumo; barras apiladas por licitante.
- Insumos: eje Y con todas las etiquetas visibles (altura dinámica, margen amplio y tickmode fijo).
- Insumos: etiqueta del eje Y cambiada a “Insumo”; radios por defecto Monto + Por licitante.

---

## [0.1.9] - 2025-10-16

### Cambios
- Producción: servidor gunicorn con 1 worker (gthread) y 4 threads; DEBUG desactivado en Render. Procfile y render.yaml ajustados.
- Normalización/precálculo: se construye df_items global durante la carga y se elimina de df principal la estructura pesada (awards, contracts, items), además de downcasting y categorías en columnas frecuentes.
- Home: evitar TypeError al mapear/fillna sobre columnas categóricas convirtiendo a string antes de mapear.
- Insumos: evitar explosión de memoria en groupby usando observed=True y forzando 'Licitante' a string.
- Procesos: mantiene ordenamiento por fecha usando columna interna fecha_dt y muestra YYYY-MM-DD.

---

## [0.1.8] - 2025-10-15

### Cambios
- Procesos Filtrados: evita IndexError cuando no hay años disponibles (value seguro en el Dropdown).
- Procesos Filtrados: ordenamiento correcto por Fecha usando columna interna datetime (fecha_dt) manteniendo formato visible YYYY-MM-DD.
- Reestructuración del DataTable de Procesos para actualizar solo "data" con sort_action="custom".

---

## [0.1.7] - 2025-10-15

### Cambios
- Forzado de logos a URLs remotas (sin dependencias de assets locales).
- Corrección de ordenamiento numérico en tablas para "Monto (Millones)" manteniendo formato visual con sufijo "M".
- Mejoras de UX en /reload-data: respuestas HTML amigables según el header Accept.
- Router tolerante a barras finales para subrutas (e.g., /acerca/).
- Ajustes de tooltips y etiquetas en gráficos (valores en millones, mayores primero).

---

## [0.1.6] - 2025-10-15
### Added
- Página "Acerca del proyecto" con autor, contacto y enlaces (repo, docs), accesible en `/acerca`.
- Botón "📖 Documentación" en el Navbar apuntando a GitHub Pages.
- Feedback HTML en `/reload-data` cuando se accede desde navegador.
- Soporte para favicon y logos locales con fallback a URLs.
- Etiquetas descriptivas en filtro "Tipo" (CDI/LPU) en Procesos Filtrados.

### Changed
- Header y Navbar más compactos (estilos en `assets/app.css`).
- Autor actualizado a "Ing. Leonardo Raúl Federico Villegas" en app, README y Sphinx.

### Fixed
- Router tolera trailing slash para rutas como `/acerca/`.
- Correcciones menores de sintaxis y docstrings.

