# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os

# Señalizar a los módulos que el build es de documentación
os.environ["SPHINX_BUILD"] = "1"

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Dashboard de Contrataciones Públicas de Mendoza — basado en el Estándar de Datos de Contratación Abierta (OCDS)'
copyright = '2025, Ing. Leonardo Raúl Federico Villegas'
author = 'Ing. Leonardo Raúl Federico Villegas'
version = '0.1.10'
release = '0.1.10'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
	"sphinx.ext.napoleon",      # Docstrings estilo Google/NumPy
	"sphinx.ext.viewcode",      # Enlaces al código fuente
	"sphinx.ext.autosummary",   # Resúmenes automáticos
	"sphinx.ext.autodoc",       # Documentación automática de módulos
]

# Generar autosummary automáticamente (si se emplea)
autosummary_generate = True

# Configurar Napoleon (docstrings en español con estilo Google)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_use_param = True
napoleon_use_rtype = True

templates_path = ['_templates']
exclude_patterns = [
	'_build',
	'_site',
	'.venv',
	'Thumbs.db',
	'.DS_Store',
	'evaluation_criteria.rst',
]

language = 'es'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_theme_options = {
	"collapse_navigation": False,
	"sticky_navigation": True,
	"navigation_depth": 3,
	"style_external_links": True,
}

# Logo y favicon (coloca los archivos en _static/)
html_logo = '_static/logo.png'
html_favicon = '_static/favicon.ico'

# Título HTML explícito para la cabecera del sitio
html_title = 'Documentación del Proyecto Dashboard de Contrataciones Públicas de Mendoza — basado en el Estándar de Datos de Contratación Abierta (OCDS)'

# Opciones para autodoc (Opción 1: mocks durante el build)
autodoc_default_options = {
	'members': True,
	'undoc-members': False,
	'inherited-members': False,
}
autodoc_mock_imports = [
	'dash',
	'dash_bootstrap_components',
	'plotly',
	'pandas',
	'requests',
]

# Agregar CSS personalizado para ocultar símbolos de parágrafo y pequeños ajustes
def setup(app):
	app.add_css_file('custom.css')
