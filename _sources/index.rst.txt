.. Proyecto Contar con Datos - Documentación principal

Documentación del Proyecto Contar con Datos
============================================================

Introducción
============
Este proyecto tiene como objetivo proporcionar una plataforma para analizar y visualizar datos de contrataciones públicas en la Provincia de Mendoza, utilizando el estándar OCDS (Open Contracting Data Standard).


Precisión de los datos y rigor metodológico
-------------------------------------------
El proyecto utiliza el estándar OCDS para garantizar que los datos sean precisos y estén estructurados de manera uniforme. Se emplean las siguientes técnicas para asegurar el rigor metodológico:

- **Validación de datos**: Uso de `pandas` y demas librerias de ciencia de datos para detectar y manejar valores nulos o inconsistentes en el dataset publicado por el organismo oficial.
- **Transformación de datos**: Limpieza y normalización de los datos teniendo en cuenta el estandar OCDS.
- **Fuentes confiables**: Los datos provienen de sistemas oficiales como el sistema COMPRAR del Gobierno de Mendoza.

Impacto y aplicabilidad
------------------------
El proyecto tiene un impacto significativo en diversas áreas:

- **Gobierno**: Mejora la transparencia y facilita la rendición de cuentas.
- **Ciudadanos**: Permite a los ciudadanos entender cómo se utilizan los recursos públicos.
- **Investigadores/ ONGs**: Proporciona un conjunto de datos estructurados para análisis avanzados. Promover proyectos sobre participacion ciudadana y vigilancia de la gestión pública. 

Casos de uso:
- Identificación de patrones de gasto público.
- Evaluación de la eficiencia en las contrataciones.
- Comparación de datos entre diferentes períodos.

Entendimiento y síntesis
-------------------------
La plataforma está diseñada para simplificar datos complejos mediante:

- **Gráficos interactivos**: Uso de `Plotly` para explorar los datos de manera visual e intuitiva.
- **Interfaz amigable**: Desarrollo con Dash y Bootstrap para garantizar una experiencia de usuario fluida.
- **Síntesis de información**: Resúmenes claros y gráficos que destacan los puntos clave.

Originalidad y creatividad
---------------------------
El proyecto se distingue por:

- **Uso innovador de tecnologías**: Integración de Dash, Plotly y el estándar OCDS.
- **Enfoque único**: Combinación de análisis de datos con visualizaciones interactivas.
- **Adaptabilidad**: La plataforma puede ser utilizada por diferentes audiencias con necesidades específicas, como el uso de otros datasets bajo el estandar OCDS.

Impacto estético y grafismo
---------------------------
El diseño visual del proyecto se centra en:

- **Estética moderna**: Uso de Dash y Bootstrap para una interfaz atractiva y responsiva.
- **Colores y estilos**: Elección de paletas de colores que mejoran la legibilidad y el impacto visual.
- **Gráficos de alta calidad**: Generación de visualizaciones claras y profesionales con `Plotly`.

Ejemplo de gráficos:
- Gráficos de barras para comparar montos entre diferentes licitantes.
- Gráficos de líneas para mostrar la evolución mensual de los gastos.
- Diagramas circulares para representar la distribución de tipos de contratación.

Tabla de Contenidos
===================
.. toctree::
   :maxdepth: 2
   :caption: Contenido Principal:

   introduction
   usage
   methodology
   api

Información
===========

.. toctree::
   :maxdepth: 1

   about
   data_sources
   license
   faq

Librerías Utilizadas
====================
En este proyecto se han utilizado diversas librerías de Python que son fundamentales en el ámbito de la ciencia de datos y el desarrollo de aplicaciones:

- **Pandas**: Para la manipulación y análisis de datos estructurados. Permite realizar operaciones como limpieza, transformación y agregación de datos de manera eficiente.
- **Plotly**: Para la creación de gráficos interactivos que facilitan la visualización de datos complejos.
- **Dash**: Para el desarrollo de aplicaciones web interactivas orientadas a la visualización de datos.
- **NumPy**: Para operaciones matemáticas y manejo de arreglos multidimensionales.
- **Sphinx**: Para la generación de documentación técnica del proyecto.

Estas herramientas son esenciales en la ciencia de datos, ya que permiten transformar datos en información útil y comprensible para la toma de decisiones.

Estandar OCDS
=============
El estándar OCDS (Open Contracting Data Standard) es un marco global para la publicación de datos de contrataciones públicas. Su importancia radica en:

- **Transparencia**: Facilita el acceso a información clara y estructurada sobre los procesos de contratación pública.
- **Comparabilidad**: Permite comparar datos entre diferentes jurisdicciones y períodos de tiempo.
- **Análisis**: Proporciona un formato uniforme que facilita el análisis y la auditoría de los datos.
- **Impacto social**: Promueve la rendición de cuentas y la lucha contra la corrupción en los procesos de contratación pública.

En este proyecto, el uso del estándar OCDS asegura que los datos sean accesibles, comprensibles y reutilizables por diferentes audiencias.

Información Adicional
=====================
Para más información sobre el estándar OCDS, visite: https://www.open-contracting.org/.

Para detalles sobre el sistema Comprar- Mendoza :https://comprar.mendoza.gov.ar/.

