# Changelog

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

