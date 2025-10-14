# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Contrataciones Públicas de Mendoza (OCDS)'
copyright = '2025, Ing. Leonardo Villegas'
author = 'Ing. Leonardo Villegas'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
	"sphinx.ext.napoleon",      # Docstrings estilo Google/NumPy
	"sphinx.ext.viewcode",      # Enlaces al código fuente
	"sphinx.ext.autosummary",   # Resúmenes automáticos (si se usan en el futuro)
	# "sphinx.ext.autodoc",     # Evitamos por ahora para no importar el módulo Dash durante el build
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
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'es'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
