# Revertimos a la versión 0.1.4 manteniendo las mejoras en los tooltips
import dash
from dash import dcc, html, Input, Output, dash_table
from dash.dash_table.Format import Format, Group, Scheme, Symbol
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json, re, os, requests, threading
import flask
import gc

# Habilitar logs detallados para Flask
import logging
# Configurar logs para que se muestren en la terminal
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

# Activar Copy-on-Write para reducir copias en memoria (pandas >= 2.1)
try:
    pd.options.mode.copy_on_write = True
except Exception:
    pass

# ------------------------------------------------------
# CONFIGURACIÓN BASE
# ------------------------------------------------------
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.COSMO],  # Tema Bootstrap mejorado
    suppress_callback_exceptions=True
)
app.title = "Dashboard de Contrataciones Públicas de Mendoza (OCDS)"
server = app.server

# Favicon: si no existe en assets/, servir el de _static/ con override de index
try:
    assets_favicon = os.path.exists(os.path.join("assets", "favicon.ico"))
    static_favicon = os.path.exists(os.path.join("_static", "favicon.ico"))
    if not assets_favicon and static_favicon:
        @app.server.route('/_static/<path:filename>')
        def serve_static_folder(filename):
            return flask.send_from_directory(os.path.abspath('_static'), filename)

        app.index_string = """
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                <link rel="icon" type="image/x-icon" href="/_static/favicon.ico" />
                {%css%}
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        """
except Exception:
    pass

# Configuración manual para servir archivos estáticos desde la carpeta 'assets'
# Agregar mensajes de depuración en la función para servir archivos estáticos
@app.server.route('/assets/<path:path>')
def serve_static_assets(path):
    logging.debug(f"Intentando servir archivo estático: {path}")
    try:
        return flask.send_from_directory('assets', path)
    except Exception as e:
        logging.error(f"Error al servir archivo estático: {e}")
        raise

# Ruta de prueba para servir un archivo específico
# Actualizar la función para usar la ruta absoluta de la carpeta 'assets'
@app.server.route('/test-file')
def serve_test_file():
    try:
        ruta_absoluta = os.path.abspath('assets')
        logging.debug(f"Ruta absoluta de la carpeta 'assets': {ruta_absoluta}")
        return flask.send_from_directory(ruta_absoluta, 'texto.txt')
    except Exception as e:
        logging.error(f"Error al servir archivo de prueba: {e}")
        return f"Error al servir archivo de prueba: {e}", 500

# Agregar mensajes de depuración para el archivo 'marca_gov.png'
@app.server.route('/test-image')
def serve_test_image():
    try:
        ruta_absoluta = os.path.abspath('assets')
        logging.debug(f"Intentando servir 'marca_gov.png' desde: {ruta_absoluta}")
        return flask.send_from_directory(ruta_absoluta, 'marca_gov.png')
    except Exception as e:
        logging.error(f"Error al servir 'marca_gov.png': {e}")
        return f"Error al servir 'marca_gov.png': {e}", 500

# Endpoint de health check ligero para PaaS / monitoreo
@app.server.route('/health')
def health():
    """Devuelve un estado simple de salud del servicio.

    Retorna un JSON con:
    - status: "ok" si el servicio responde.
    - rows: cantidad de filas cargadas en el DataFrame principal (0 durante build de docs o si no hay datos).
    - sphinx_build: flag indicando si se está ejecutando en modo build de documentación.
    """
    try:
        return flask.jsonify(status="ok", rows=int(len(df)), sphinx_build=SPHINX_BUILD), 200
    except Exception as e:
        logging.exception("Fallo en /health")
        return flask.jsonify(status="error", error=str(e)), 500

# ------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------
def cargar_ocds(ruta):
    """Carga un JSON OCDS desde una URL o desde una ruta local.

    Parámetros
    ----------
    ruta : str
        Ruta absoluta/relativa del archivo JSON o URL HTTP(S).

    Retorna
    -------
    dict
        Objeto Python con el contenido JSON del release OCDS.

    Lanza
    -----
    ValueError
        Si la ruta no es válida ni URL ni archivo existente.
    """
    # Sanitizar ruta (eliminar comillas accidentales y espacios)
    ruta = ruta.strip().strip('"').strip("'")
    if ruta.startswith("http"):
        # Añadimos timeout y un User-Agent para entornos con filtros
        headers = {"User-Agent": "OCDS-Mendoza-Dashboard/1.0"}
        resp = requests.get(ruta, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    elif os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError(f"No se reconoce la ruta: {ruta}")

def extraer_contratos(data):
    """Transforma el JSON OCDS en un DataFrame tabular de contratos/adjudicaciones.

    Recorre la lista de ``releases`` y normaliza campos relevantes para
    análisis y visualización (fecha, tender_id, licitante, proveedor, monto,
    tipo de contratación estimado, etc.).

    Parámetros
    ----------
    data : dict
        Estructura JSON con el/los releases en formato OCDS.

    Retorna
    -------
    pandas.DataFrame
        Tabla con registros por proveedor/adjudicación.
    """
    registros = []
    for rel in data.get("releases", []):
        fecha = (
            rel.get("tender", {}).get("period", {}).get("startDate")
            or (rel.get("awards", [{}])[0].get("date") if rel.get("awards") else None)
            or (rel.get("contracts", [{}])[0].get("dateSigned") if rel.get("contracts") else None)
            or rel.get("date")
        )
        tender = rel.get("tender", {})
        buyer = rel.get("buyer", {})
        awards = rel.get("awards", [])
        contracts = rel.get("contracts", [])

        # Guardamos submissionMethodDetails si existe (ayuda a inferir tipo)
        submission_details = tender.get("submissionMethodDetails")

        tender_id = tender.get("id")
        contrato_desc = None
        if not tender_id and contracts:
            desc = contracts[0].get("description", "") or ""
            contrato_desc = desc
            match = re.search(r"Proceso Nº ([0-9\-]+-[A-Z]+\d+)", desc)
            if match:
                tender_id = match.group(1)

        # utilitario para mapear award->contract y obtener orden de compra por proveedor
        def _obtener_orden_compra(_awards, _contracts, _proveedor):
            if not _awards or not _contracts or not _proveedor:
                return None
            try:
                for awd in _awards:
                    if awd.get("suppliers"):
                        for sup in awd["suppliers"]:
                            if sup.get("name") == _proveedor:
                                aw_id = awd.get("id")
                                for c in (_contracts or []):
                                    if c.get("awardID") == aw_id:
                                        return c.get("id")
                return None
            except Exception:
                return None

        for aw in awards:
            monto = aw.get("value", {}).get("amount")
            moneda = aw.get("value", {}).get("currency")
            suppliers = aw.get("suppliers", [])
            if suppliers:
                for sup in suppliers:
                    proveedor_nombre = sup.get("name")
                    registros.append({
                        "fecha": fecha,
                        "tender_id": tender_id,
                        "titulo": tender.get("title"),
                        "licitante": buyer.get("name"),
                        "proveedor": proveedor_nombre,
                        "monto": monto,
                        "moneda": moneda,
                        "contrato_desc": contrato_desc,
                        "submission_details": submission_details,
                        "orden_compra": _obtener_orden_compra(awards, contracts, proveedor_nombre)
                    })
            else:
                registros.append({
                    "fecha": fecha,
                    "tender_id": tender_id,
                    "titulo": tender.get("title"),
                    "licitante": buyer.get("name"),
                    "proveedor": None,
                    "monto": monto,
                    "moneda": moneda,
                    "contrato_desc": contrato_desc,
                    "submission_details": submission_details,
                    "orden_compra": None
                })

    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["año"] = df["fecha"].dt.year
    return df

def detectar_tipo(tender_id, titulo=None, contrato_desc=None, submission_details=None):
    """Intenta clasificar el tipo de contratación.

    La heurística busca primero un sufijo en ``tender_id`` (p. ej. ``-LPU99``),
    y si no está disponible, infiere desde ``titulo``, ``submission_details`` o
    ``contrato_desc`` buscando palabras clave.

    Parámetros
    ----------
    tender_id : str | None
        Identificador del proceso licitatorio.
    titulo : str | None
        Título del proceso (si existe).
    contrato_desc : str | None
        Descripción de contrato (fallback).
    submission_details : str | None
        Texto con detalles del método de presentación (si existe).

    Retorna
    -------
    str
        Uno de ``{"LPU", "CDI", "Otro"}``.
    """
    # 1) desde tender_id
    if tender_id and not pd.isna(tender_id):
        m = re.search(r"-([A-Z]{2,4})\d+$", str(tender_id))
        if m:
            return m.group(1)

    # 2) fallback desde texto del título / submission_details / contrato_desc
    txt = " ".join(filter(None, [str(titulo or "").lower(), str(submission_details or "").lower(), str(contrato_desc or "").lower()]))
    if "contratación directa" in txt or "contratacion directa" in txt or "contratación-directa" in txt:
        return "CDI"
    if "licitación pública" in txt or "licitacion publica" in txt or "licitacion pública" in txt or "licitacion-publica" in txt or "licitación-publica" in txt:
        return "LPU"

    # si no se detecta, devolver "Otro"
    return "Otro"

def format_mill_int(x):
    """Formatea números en millones para su uso en tablas.

    - Recibe un valor numérico que representa millones (p. ej. ``54137.6``).
    - Redondea al entero (``54137``).
    - Devuelve un texto con separador de miles ``.`` y sufijo ``M``
      (``"54.137M"`` en el ejemplo).

    Parámetros
    ----------
    x : float | int | None
        Valor numérico en millones.

    Retorna
    -------
    str
        Cadena formateada o ``"-"`` si el valor no es válido.
    """
    try:
        if pd.isna(x):
            return "-"
        val = int(round(float(x)))
        s = f"{val:,}".replace(",", ".")
        return f"{s}M"
    except Exception:
        return "-"

def format_mill_hover(x, decimals=3):
    """Formatea valores en millones para tooltips (hover) en gráficos.

    Muestra el valor con ``decimals`` decimales y sufijo ``M``.

    Parámetros
    ----------
    x : float | int | None
        Valor en millones.
    decimals : int
        Cantidad de decimales a mostrar (por defecto 3).

    Retorna
    -------
    str
        Cadena formateada o ``"-"`` si el valor no es válido.
    """
    if pd.isna(x):
        return "-"
    val = float(x)
    # mostramos con 3 decimales (ej: 54137.600) y añadimos 'M'
    return f"{val:,.3f}".replace(",", ".") + "M"

# Función para capitalizar títulos
def capitalize_title(title):
    return " ".join(word.capitalize() for word in title.split())

# ------------------------------------------------------
# CARGA DE DATOS y normalizaciones
# ------------------------------------------------------
# Si se está construyendo la documentación (SPHINX_BUILD=1), evitamos cargar datos reales
SPHINX_BUILD = os.getenv("SPHINX_BUILD") == "1"
LAZY_LOAD = os.getenv("LAZY_LOAD") == "1"  # Si está activo difiere la carga real hasta que se invoque manualmente

# Variables globales de dataset
_DEFAULT_OCDS_URL = "https://datosabiertos-compras.mendoza.gov.ar/descargar-json/02/20250810_release.json"
_RAW_ENV_URL = os.getenv("OCDS_JSON_URL")
if _RAW_ENV_URL is None or _RAW_ENV_URL.strip() == "":
    URL_JSON = _DEFAULT_OCDS_URL
else:
    URL_JSON = _RAW_ENV_URL.strip()
data = {"releases": []}
df = pd.DataFrame({
    "fecha": pd.to_datetime(pd.Series([], dtype="datetime64[ns]")),
    "año": pd.Series([], dtype="Int64"),
    "monto": pd.Series([], dtype="float"),
    "monto_millones": pd.Series([], dtype="float"),
    "tipo_contratacion": pd.Series([], dtype="string"),
    "licitante": pd.Series([], dtype="string"),
    "tender_id": pd.Series([], dtype="string"),
    "titulo": pd.Series([], dtype="string"),
    "proveedor": pd.Series([], dtype="string"),
})
df_items = pd.DataFrame({
    "año": pd.Series([], dtype="Int64"),
    "Código": pd.Series([], dtype="string"),
    "Descripción corta": pd.Series([], dtype="string"),
    "Licitante": pd.Series([], dtype="string"),
    "Monto (Millones)": pd.Series([], dtype="float"),
})
_DATA_LOADED = False
_DATA_LOCK = threading.Lock()
_DATA_ERROR = None

def _cargar_datos_internamente(max_retries: int = 3, base_delay: float = 2.0):
    global data, df, df_items, _DATA_LOADED, _DATA_ERROR
    logging.info("Iniciando carga de datos OCDS desde %s", URL_JSON)
    last_err = None
    for intento in range(1, max_retries + 1):
        try:
            # Si STREAM_PARSE=1 y es URL http(s), usar parseo incremental para reducir memoria
            use_stream = os.getenv("STREAM_PARSE") == "1" and URL_JSON.startswith("http")
            raw = None
            if use_stream:
                logging.info("Usando parseo streaming (ijson)")
            else:
                raw = cargar_ocds(URL_JSON)
            break
        except Exception as e:
            last_err = e
            wait = base_delay * intento
            logging.warning("Intento %d/%d fallo al descargar dataset (%s). Reintentando en %.1fs", intento, max_retries, e, wait)
            if intento == max_retries:
                logging.error("Fallo definitivo tras %d intentos: %s", max_retries, e)
                raise
            import time as _t; _t.sleep(wait)
    # Construcción de dataframes: streaming si se solicitó
    if os.getenv("STREAM_PARSE") == "1" and URL_JSON.startswith("http"):
        try:
            import ijson  # type: ignore  # import local opcional
        except Exception as e:
            logging.warning("STREAM_PARSE=1 pero no se pudo importar ijson (%s). Volviendo a método estándar.", e)
            raw = cargar_ocds(URL_JSON)
            df_local = extraer_contratos(raw)
        else:
            # Parseo incremental de releases
            registros = []
            items_reg = []
            headers = {"User-Agent": "OCDS-Mendoza-Dashboard/1.0"}
            with requests.get(URL_JSON, headers=headers, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                resp.raw.decode_content = True
                for rel in ijson.items(resp.raw, 'releases.item'):
                    try:
                        tender = rel.get("tender", {}) or {}
                        buyer = (rel.get("buyer", {}) or {}).get("name")
                        awards = rel.get("awards", []) or []
                        contracts = rel.get("contracts", []) or []
                        fecha = (
                            tender.get("period", {}).get("startDate")
                            or (awards[0].get("date") if awards else None)
                            or (contracts[0].get("dateSigned") if contracts else None)
                            or rel.get("date")
                        )
                        tender_id = tender.get("id")
                        contrato_desc = None
                        if not tender_id and contracts:
                            desc = contracts[0].get("description", "") or ""
                            contrato_desc = desc
                            m = re.search(r"Proceso Nº ([0-9\-]+-[A-Z]+\d+)", desc)
                            if m:
                                tender_id = m.group(1)
                        submission_details = tender.get("submissionMethodDetails")

                        def _obtener_orden_compra_stream(_awards, _contracts, _proveedor):
                            if not _awards or not _contracts or not _proveedor:
                                return None
                            try:
                                for awd in _awards:
                                    if awd.get("suppliers"):
                                        for sup in awd["suppliers"]:
                                            if sup.get("name") == _proveedor:
                                                aw_id = awd.get("id")
                                                for c in (_contracts or []):
                                                    if c.get("awardID") == aw_id:
                                                        return c.get("id")
                                return None
                            except Exception:
                                return None

                        # Registros por proveedor en awards
                        if awards:
                            for aw in awards:
                                monto = aw.get("value", {}).get("amount")
                                moneda = aw.get("value", {}).get("currency")
                                sups = aw.get("suppliers", []) or []
                                for sup in sups or [{}]:
                                    proveedor_nombre = sup.get("name") if sup else None
                                    registros.append({
                                        "fecha": fecha,
                                        "tender_id": tender_id,
                                        "titulo": tender.get("title"),
                                        "licitante": buyer,
                                        "proveedor": proveedor_nombre,
                                        "monto": monto,
                                        "moneda": moneda,
                                        "contrato_desc": contrato_desc,
                                        "submission_details": submission_details,
                                        "orden_compra": _obtener_orden_compra_stream(awards, contracts, proveedor_nombre)
                                    })
                        else:
                            registros.append({
                                "fecha": fecha,
                                "tender_id": tender_id,
                                "titulo": tender.get("title"),
                                "licitante": buyer,
                                "proveedor": None,
                                "monto": (awards[0].get("value", {}).get("amount") if awards else None),
                                "moneda": (awards[0].get("value", {}).get("currency") if awards else None),
                                "contrato_desc": contrato_desc,
                                "submission_details": submission_details,
                                "orden_compra": None
                            })

                        # Items por release (monto total del release en millones)
                        try:
                            monto_millones_rel = 0.0
                            for aw in awards:
                                amt = aw.get("value", {}).get("amount")
                                if amt is not None:
                                    monto_millones_rel += float(amt) / 1_000_000.0
                        except Exception:
                            monto_millones_rel = 0.0
                        fecha_dt = pd.to_datetime(fecha, errors="coerce") if fecha else pd.NaT
                        año = int(fecha_dt.year) if pd.notna(fecha_dt) else None
                        for it in (tender.get("items", []) or []):
                            codigo = (it.get("classification", {}) or {}).get("id") or it.get("id")
                            descripcion = it.get("description")
                            qty_raw = it.get("quantity")
                            try:
                                cantidad = float(qty_raw) if qty_raw is not None and str(qty_raw).strip() != "" else 0.0
                            except Exception:
                                cantidad = 0.0
                            if codigo and descripcion:
                                items_reg.append({
                                    "año": año,
                                    "Código": str(codigo),
                                    "Descripción corta": str(descripcion)[:80],
                                    "Licitante": buyer,
                                    "Monto (Millones)": float(monto_millones_rel or 0.0),
                                    "Cantidad": cantidad
                                })
                    except Exception:
                        # No abortar por un release malformado; continuar
                        continue
            # Crear df_local y df_items
            df_local = pd.DataFrame(registros)
            if not df_local.empty:
                df_local["fecha"] = pd.to_datetime(df_local["fecha"], errors="coerce")
                df_local["año"] = df_local["fecha"].dt.year
            df_items = pd.DataFrame(items_reg)
    else:
        df_local = extraer_contratos(raw)
    if not df_local.empty:
        df_local["tipo_contratacion"] = df_local.apply(
            lambda r: detectar_tipo(r.get("tender_id"), r.get("titulo"), r.get("contrato_desc"), r.get("submission_details")),
            axis=1
        )
        # Numéricos
        df_local["monto"] = pd.to_numeric(df_local["monto"], errors="coerce").fillna(0.0)
        df_local["monto_millones"] = df_local["monto"] / 1_000_000.0

        # Precálculos de fecha y tipos eficientes
        df_local["fecha_dt"] = pd.to_datetime(df_local["fecha"], errors="coerce")
        df_local["fecha"] = df_local["fecha_dt"]  # mantener dtype datetime64
        df_local["año"] = df_local["fecha_dt"].dt.year.astype("Int16")

        # Limitar a últimos N años para reducir memoria (si se define)
        try:
            last_n = int(os.getenv("OCDS_LIMIT_LAST_YEARS", "0"))
        except Exception:
            last_n = 0
        if last_n and last_n > 0:
            max_year = int(df_local["año"].max()) if not df_local["año"].isna().all() else None
            if max_year is not None:
                min_year = max_year - last_n + 1
                df_local = df_local[df_local["año"] >= min_year]

        # Construir df_items global para página Insumos SIN guardar 'items' en df_local
        items_reg = []
        for rel in raw.get("releases", []) or []:
            try:
                tender = rel.get("tender", {}) or {}
                buyer = (rel.get("buyer", {}) or {}).get("name")
                # Fecha/año similar a extraer_contratos
                fecha = (
                    tender.get("period", {}).get("startDate")
                    or (rel.get("awards", [{}])[0].get("date") if rel.get("awards") else None)
                    or (rel.get("contracts", [{}])[0].get("dateSigned") if rel.get("contracts") else None)
                    or rel.get("date")
                )
                año = pd.to_datetime(fecha, errors="coerce").year if fecha else None
                items_list = tender.get("items", []) or []
                if not items_list:
                    continue
                # monto_millones: tomar por award (por compatibilidad con implementación previa)
                monto_millones_rel = 0.0
                awards = rel.get("awards", []) or []
                for aw in awards:
                    amt = aw.get("value", {}).get("amount")
                    try:
                        if amt is not None:
                            monto_millones_rel += float(amt) / 1_000_000.0
                    except Exception:
                        pass
                for it in items_list:
                    codigo = (it.get("classification", {}) or {}).get("id") or it.get("id")
                    descripcion = it.get("description")
                    qty_raw = it.get("quantity")
                    try:
                        cantidad = float(qty_raw) if qty_raw is not None and str(qty_raw).strip() != "" else 0.0
                    except Exception:
                        cantidad = 0.0
                    if codigo and descripcion:
                        items_reg.append({
                            "año": int(año) if año is not None else None,
                            "Código": str(codigo),
                            "Descripción corta": str(descripcion)[:80],
                            "Licitante": buyer,
                            "Monto (Millones)": float(monto_millones_rel or 0.0),
                            "Cantidad": cantidad
                        })
            except Exception:
                # Continuar si un release tiene formato inesperado
                continue
        df_items = pd.DataFrame(items_reg)
        if not df_items.empty:
            df_items["año"] = df_items["año"].astype("Int16")
            df_items["Código"] = df_items["Código"].astype("string")
            df_items["Descripción corta"] = df_items["Descripción corta"].astype("string")
            try:
                df_items["Licitante"] = df_items["Licitante"].astype("category")
            except Exception:
                pass
            df_items["Monto (Millones)"] = pd.to_numeric(df_items["Monto (Millones)"], errors="coerce", downcast="float").fillna(0.0)
            df_items["Cantidad"] = pd.to_numeric(df_items["Cantidad"], errors="coerce", downcast="float").fillna(0.0)

        # Downcast/categorías en df principal
        df_local["monto"] = pd.to_numeric(df_local["monto"], errors="coerce", downcast="float").fillna(0.0)
        df_local["monto_millones"] = pd.to_numeric(df_local["monto_millones"], errors="coerce", downcast="float").fillna(0.0)
        for col in ["licitante", "tipo_contratacion", "moneda"]:
            if col in df_local.columns:
                try:
                    df_local[col] = df_local[col].astype("category")
                except Exception:
                    pass

        # Ya no guardamos columnas pesadas; mantener solo columnas necesarias
    data = raw if raw is not None else {"releases": []}
    df = df_local
    _DATA_LOADED = True
    _DATA_ERROR = None
    # Sugerir GC explícito tras carga
    try:
        gc.collect()
    except Exception:
        pass
    logging.info("Carga de datos completa. Filas=%d", len(df))

def ensure_data_loaded(force: bool = False):
    """Garantiza que los datos estén cargados (lazy si LAZY_LOAD=1)."""
    global _DATA_LOADED, _DATA_ERROR
    if SPHINX_BUILD:
        return
    if _DATA_LOADED and not force:
        return
    with _DATA_LOCK:
        if _DATA_LOADED and not force:
            return
        try:
            _cargar_datos_internamente()
        except Exception as e:
            _DATA_ERROR = str(e)
            logging.exception("Fallo al cargar datos OCDS (se usará DataFrame vacío)")

# Carga inmediata salvo que estemos en build de docs o modo lazy
if not SPHINX_BUILD and not LAZY_LOAD:
    ensure_data_loaded()

# Endpoint opcional para forzar recarga manual (útil en PaaS si falló al inicio)
@app.server.route('/reload-data')
def reload_data_route():
    if SPHINX_BUILD:
        # Si el navegador pide HTML, devolvemos una pequeña página informativa
        if 'text/html' in flask.request.headers.get('Accept', ''):
            return (
                """
                <html><body style='font-family:system-ui'>
                <h3>Recarga de datos</h3>
                <p>Modo SPHINX_BUILD activo: no se carga dataset.</p>
                <p><a href='/'>Volver al inicio</a></p>
                </body></html>
                """,
                200,
                {"Content-Type": "text/html"}
            )
        return flask.jsonify(message="Modo SPHINX_BUILD: no se carga dataset"), 200
    ensure_data_loaded(force=True)
    if _DATA_ERROR:
        if 'text/html' in flask.request.headers.get('Accept', ''):
            return (
                f"""
                <html><body style='font-family:system-ui'>
                <h3>Recarga de datos</h3>
                <p style='color:#b00020'>Error: {_DATA_ERROR}</p>
                <p><a href='/'>Volver al inicio</a></p>
                </body></html>
                """,
                500,
                {"Content-Type": "text/html"}
            )
        return flask.jsonify(status="error", error=_DATA_ERROR), 500
    # OK
    if 'text/html' in flask.request.headers.get('Accept', ''):
        return (
            f"""
            <html><body style='font-family:system-ui'>
            <h3>Recarga de datos</h3>
            <p>Recarga completada. Filas: {len(df)}</p>
            <p><a href='/'>Volver al inicio</a></p>
            </body></html>
            """,
            200,
            {"Content-Type": "text/html"}
        )
    return flask.jsonify(status="ok", rows=len(df)), 200

# ------------------------------------------------------
# ENCABEZADO CON ESCUDO
# ------------------------------------------------------
# Determinar logos: siempre usar URLs (no usar assets locales)
LOGO_GOV_SRC = "https://mza-dicaws-portal-uploads-media-prod.s3.amazonaws.com/principal/uploads/2025/10/SITIO-AC_200x200-1-300x300-1.png"
LOGO_OCDS_SRC = "https://ocp.imgix.net/wp-content/uploads/2020/01/OCDS-logo-grey.png?auto=format&w=1800"

header = dbc.Navbar(
    dbc.Container(
        dbc.Row([
            dbc.Col(
                html.A(
                    html.Img(
                        src=LOGO_GOV_SRC,
                        style={"height": "48px"}
                    ),
                    href="https://www.mendoza.gov.ar/compras/",
                    target="_blank"
                ),
                width="auto"
            ),
            dbc.Col(
                html.Div(
                    html.H2(
                        "Dashboard de Contrataciones Públicas de Mendoza (OCDS)",
                        className="text-white text-center",
                        style={"fontSize": "1.25rem", "margin": 0}
                    ),
                ),
                align="center"
            ),
            dbc.Col(
                html.A(
                    html.Img(
                        src=LOGO_OCDS_SRC,
                        style={"height": "36px", "backgroundColor": "white", "padding": "2px", "borderRadius": "4px"}
                    ),
                    href="https://www.open-contracting.org/",
                    target="_blank"
                ),
                width="auto"
            )
        ], align="center", className="g-2"),
    ),
    color="dark",
    dark=True,
    className="mb-3"
)

# ------------------------------------------------------
# LAYOUT BASE
# ------------------------------------------------------
app.layout = dbc.Container([
    header,
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("🏠 Home", href="/", active="exact")),
            dbc.NavItem(dbc.NavLink("🏷️ Insumos", href="/insumos", active="exact")),
            dbc.NavItem(dbc.NavLink("🔎 Procesos", href="/procesos", active="exact")),
            dbc.NavItem(dbc.NavLink("ℹ️ Acerca del proyecto", href="/acerca", active="exact")),
            dbc.NavItem(dbc.NavLink("📖 Documentación", href="https://leonardorf.github.io/contrataciones-publicas-OCDS/", target="_blank")),
        ],
        brand="📊 Dashboard OCDS Mendoza",
        brand_href="/",
        color="primary",
        dark=True,
        className="mb-4",
        style={"fontSize": "90%"}
    ),
    dcc.Location(id="url"),
    dcc.Store(id="reload-done"),
    html.Div(id="page-content"),
    html.P("Versión 0.1.10 – Dashboard OCDS Mendoza", className="text-muted small text-end")
], fluid=True)

# ------------------------------------------------------
# Página HOME
# ------------------------------------------------------
# Restauramos la funcionalidad completa de layout_home con tablas y gráficos
def layout_home():
    """Genera el layout de la página principal (Home).

    Incluye un selector de año, tarjetas con totales y gráficos de evolución,
    distribución por tipo de contratación y rankings de licitantes.

    Retorna
    -------
    dash.html.Div
        Contenedor con los componentes Dash del layout Home.
    """
    años = sorted(df["año"].dropna().unique())
    año_sel = años[-1] if años else None
    # Rango seguro cuando no hay datos aún (LAZY_LOAD) o fechas NaT
    try:
        if df.empty or df["fecha"].dropna().empty:
            rango = "sin datos aún"
        else:
            fmin = pd.to_datetime(df["fecha"], errors="coerce").min()
            fmax = pd.to_datetime(df["fecha"], errors="coerce").max()
            rango = f"{fmin.date()} → {fmax.date()}" if pd.notna(fmin) and pd.notna(fmax) else "sin datos aún"
    except Exception:
        rango = "sin datos aún"
    return html.Div([
        html.H5(f"📅 Rango de fechas detectado en último Dataset publicado: {rango}"),
        html.P(
            "OCDS (Open Contracting Data Standard) es un estándar para publicar datos de contrataciones públicas "
            "en formato uniforme. Usarlo ayuda a comparar, analizar y auditar los procesos de compra pública.",
            style={"fontStyle": "italic"}
        ),
        html.P(
            "Información correspondiente a los procesos de compras llevados a cabo por las diferentes reparticiones del Gobierno de la Provincia de Mendoza. "
            "Los datos corresponden a todos los bienes y servicios adquiridos por el Gobierno de la Provincia de Mendoza a través del sistema COMPRAR.",
            style={"fontStyle": "italic"}
        ),
        dcc.Dropdown(
            id="año-selector-home",
            options=[{"label": str(a), "value": a} for a in años],
            value=año_sel,
            clearable=False
        ),
        html.Div(id="contenido-home"),
        html.Hr(),
    ])

# Ajustamos los tooltips para eliminar los decimales en los montos
@app.callback(Output("contenido-home", "children"), Input("año-selector-home", "value"))
def actualizar_home(año_sel):
    """Callback que actualiza el contenido de Home cuando cambia el año.

    Parámetros
    ----------
    año_sel : int
        Año seleccionado en el ``Dropdown``.

    Retorna
    -------
    dash.html.Div
        Componentes con tabla de totales y gráficos correspondientes.
    """
    if año_sel is None or df.empty:
        return html.Div([
            html.P("No hay datos disponibles (dataset vacío o carga diferida)."),
            html.Button("Forzar recarga de datos", id="btn-reload-data", n_clicks=0, className="btn btn-primary"),
            dcc.Interval(id="reload-poller", interval=3000, n_intervals=0, disabled=True),
            html.Div(id="reload-status", className="mt-2 text-muted")
        ])
    df_f = df[df["año"] == año_sel].copy()

    # --- Totales por tipo (numérico) y versión para mostrar formateada ---
    totales = df_f.groupby("tipo_contratacion", as_index=False)["monto_millones"].sum()
    # Mapear códigos a etiquetas descriptivas
    mapping_tipos = {
        "CDI": "Contratación Directa (CDI)",
        "LPU": "Licitación Pública (LPU)"
    }
    # Evitar conflictos con dtype 'category' convirtiendo a string antes de mapear
    _tc_series = totales["tipo_contratacion"].astype("string")
    totales["tipo_contratacion_ext"] = _tc_series.map(mapping_tipos).fillna(_tc_series)  # fallback a valor original
    totales["Monto (Millones)"] = totales["monto_millones"].apply(format_mill_int)
    totales_display = totales[["tipo_contratacion_ext", "Monto (Millones)"]].rename(columns={"tipo_contratacion_ext": "Tipo Contratación"})

    tabla_totales = dash_table.DataTable(
        id="tabla-totales",
        columns=[{"name": c, "id": c} for c in totales_display.columns],
        data=totales_display.to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=10
    )

    # --- Evolución mensual (gráfico) ---
    df_mes = df_f.copy()
    df_mes["mes"] = df_mes["fecha"].dt.month
    df_mes = df_mes.groupby("mes", as_index=False).agg(total_monto=("monto_millones", "sum"))

    fig_mes = px.line(df_mes, x="mes", y="total_monto", title=capitalize_title(f"Evolución mensual ({año_sel})"),
                      labels={"mes": "Mes", "total_monto": "Monto (Millones)"})
    fig_mes.update_traces(hovertemplate="Mes=%{x}<br>Monto=%{y:.0f}M")

    # --- Monto por tipo de contratación (gráfico) ---
    dist_tipo = df_f.groupby("tipo_contratacion", as_index=False)["monto_millones"].sum()
    dist_tipo = dist_tipo[dist_tipo["monto_millones"] > 0]
    # Evitar conflictos con dtype 'category' convirtiendo a string antes de mapear
    _dtc_series = dist_tipo["tipo_contratacion"].astype("string")
    dist_tipo["tipo_contratacion_ext"] = _dtc_series.map(mapping_tipos).fillna(_dtc_series)
    fig_pie = px.pie(dist_tipo, values="monto_millones", names="tipo_contratacion_ext", title=capitalize_title(f"Monto por tipo de contratación ({año_sel})"))
    fig_pie.update_traces(hovertemplate="%{label}: %{value:.0f}M")

    # --- Top 10 licitantes (año) ---
    top10 = df_f.groupby("licitante", as_index=False)["monto_millones"].sum().nlargest(10, "monto_millones")
    order_top10 = top10.sort_values("monto_millones", ascending=False)["licitante"].tolist()
    fig_top10 = px.bar(
        top10,
        x="monto_millones",
        y="licitante",
        orientation="h",
        title=capitalize_title(f"Top 10 Licitantes ({año_sel})"),
        labels={"monto_millones": "Monto (Millones)", "licitante": "Licitante"},
        category_orders={"licitante": order_top10}
    )
    fig_top10.update_traces(hovertemplate="Licitante=%{y}<br>Monto=%{x:.0f}M")
    # Etiquetas de datos en millones, fuera de la barra, para mejor lectura
    fig_top10.update_traces(texttemplate="%{x:.0f}M", textposition="outside", cliponaxis=False)

    # --- Top 20 licitantes (total) ---
    top20 = df.groupby("licitante", as_index=False)["monto_millones"].sum().nlargest(20, "monto_millones")
    order_top20 = top20.sort_values("monto_millones", ascending=False)["licitante"].tolist()
    fig_top20 = px.bar(
        top20,
        x="monto_millones",
        y="licitante",
        orientation="h",
        title=capitalize_title("Top 20 Licitantes (Total)"),
        labels={"monto_millones": "Monto (Millones)", "licitante": "Licitante"},
        category_orders={"licitante": order_top20}
    )
    fig_top20.update_traces(hovertemplate="Licitante=%{y}<br>Monto=%{x:.0f}M")
    # Etiquetas de datos en millones, fuera de la barra, para mejor lectura
    fig_top20.update_traces(texttemplate="%{x:.0f}M", textposition="outside", cliponaxis=False)

    # --- Top 30 montos (tabla) ---
    top30 = df_f.sort_values("monto", ascending=False).head(30).copy()
    # Usar dato numérico y aplicar formato visual en DataTable (permite orden numérico correcto)
    top30["Monto (Millones)"] = top30["monto_millones"]
    top30["fecha"] = top30["fecha"].dt.strftime("%Y-%m-%d")
    top30 = top30.rename(columns={"tender_id": "Proceso", "titulo": "Título", "licitante": "Licitante", "proveedor": "Proveedor"})
    cols_top30 = ["fecha", "Proceso", "Título", "Licitante", "Proveedor", "Monto (Millones)"]
    columns_out_top30 = [
        {"name": "Fecha", "id": "fecha"},
        {"name": "Proceso", "id": "Proceso"},
        {"name": "Título", "id": "Título"},
        {"name": "Licitante", "id": "Licitante"},
        {"name": "Proveedor", "id": "Proveedor"},
        {
            "name": "Monto (Millones)",
            "id": "Monto (Millones)",
            "type": "numeric",
            "format": Format(
                scheme=Scheme.fixed,
                precision=0,
                group=Group.yes,
                groups=3
            ).group_delimiter('.')
             .decimal_delimiter(',')
             .symbol(Symbol.yes)
             .symbol_suffix('M')
        }
    ]
    tabla_top30 = dash_table.DataTable(
        id="tabla-top30",
        columns=columns_out_top30,
        data=top30[cols_top30].to_dict("records"),
        style_table={"overflowX": "auto"},
        style_cell={"fontSize": "70%"},  # Reducir el tamaño de la fuente al 70%
        page_size=15,
        sort_action="native",
    )

    return html.Div([
        html.H4(f"💰 Total Contratado Por Tipo De Contratación ({año_sel})"),
        tabla_totales,
        dcc.Graph(figure=fig_mes),
        dcc.Graph(figure=fig_pie),
        dcc.Graph(figure=fig_top10),
        dcc.Graph(figure=fig_top20),
        html.H4(f"🏆 Top 30 Montos Más Altos ({año_sel})"),
        tabla_top30
    ])

# ------------------------------------------------------
# Página INSUMOS
# ------------------------------------------------------
def layout_insumos():
    """Genera el layout de la página de Insumos más contratados.

    Retorna
    -------
    dash.html.Div
        Contenedor con el selector de año y el espacio para resultados.
    """
    años = sorted(df["año"].dropna().unique())
    año_sel = años[-1] if años else None
    return html.Div([
        html.H4("🏷️ Top Insumos Más Contratados"),
        dcc.Dropdown(
            id="año-selector-insumos",
            options=[{"label": str(a), "value": a} for a in años],
            value=año_sel,
            clearable=False
        ),
        dbc.Row([
            dbc.Col(
                dcc.RadioItems(
                    id="insumos-medida",
                    options=[
                        {"label": " Monto (M)", "value": "monto"},
                        {"label": " Cantidad", "value": "cantidad"},
                    ],
                    value="monto",
                    inline=True,
                ), md="auto"
            ),
            dbc.Col(
                dcc.RadioItems(
                    id="insumos-vista",
                    options=[
                        {"label": " Agregado (Ítem)", "value": "agregado"},
                        {"label": " Por licitante", "value": "detalle"},
                    ],
                    value="detalle",
                    inline=True,
                ), md="auto"
            ),
        ], className="my-2"),
        html.Div(id="contenido-insumos"),
        html.Hr()
    ])

@app.callback(
    Output("contenido-insumos", "children"),
    Input("año-selector-insumos", "value"),
    Input("insumos-medida", "value"),
    Input("insumos-vista", "value"),
)
def actualizar_insumos(año_sel, medida, vista):
    """Callback que arma el Top de insumos y su gráfico para el año dado.

    Parámetros
    ----------
    año_sel : int
        Año seleccionado.

    Retorna
    -------
    dash.html.Div
        Tabla y gráfico de barras con los insumos más contratados.
    """
    # Usar df_items global precomputado
    df_items_year = df_items[df_items["año"] == año_sel].copy()
    if df_items_year.empty:
        return html.Div("⚠️ No se encontraron items para este año.")
    # Evitar producto cartesiano por dtype 'category': convertir 'Licitante' a string y usar observed=True
    try:
        df_items_year["Licitante"] = df_items_year["Licitante"].astype("string")
    except Exception:
        pass
    # Si el usuario selecciona 'cantidad' y la columna no existe, crearla con ceros
    if medida == "cantidad" and "Cantidad" not in df_items_year.columns:
        df_items_year["Cantidad"] = 0.0
    # Configuración según medida y vista
    medida = (medida or "monto").lower()
    vista = (vista or "agregado").lower()
    metric_col = "Monto (Millones)" if medida == "monto" else "Cantidad"

    # 1) Tabla: Top 20 según vista
    group_cols_detalle = ["Código", "Descripción corta", "Licitante"] if vista == "detalle" else ["Código", "Descripción corta"]
    df_top_tabla = (
        df_items_year
        .groupby(group_cols_detalle, as_index=False, observed=True)[metric_col]
        .sum()
        .rename(columns={metric_col: "Valor"})
        .sort_values("Valor", ascending=False)
        .head(20)
    )

    # Definir columnas de la tabla dinámicamente
    cols_base = [
        {"name": "Código", "id": "Código"},
        {"name": "Descripción corta", "id": "Descripción corta"},
    ]
    if vista == "detalle":
        cols_base.append({"name": "Licitante", "id": "Licitante"})

    if medida == "monto":
        valor_col = {
            "name": "Monto (Millones)",
            "id": "Valor",
            "type": "numeric",
            "format": Format(
                scheme=Scheme.fixed,
                precision=0,
                group=Group.yes,
                groups=3
            ).group_delimiter('.')
             .decimal_delimiter(',')
             .symbol(Symbol.yes)
             .symbol_suffix('M')
        }
    else:
        valor_col = {
            "name": "Cantidad",
            "id": "Valor",
            "type": "numeric",
            "format": Format(
                scheme=Scheme.fixed,
                precision=0,
                group=Group.yes,
                groups=3
            ).group_delimiter('.')
             .decimal_delimiter(',')
        }
    columns_out_insumos = cols_base + [valor_col]

    tabla = dash_table.DataTable(
        id="tabla-insumos",
        columns=columns_out_insumos,
        data=df_top_tabla.to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=15,
        sort_action="native"
    )

    # 2) Gráfico: Top 20 según vista
    if vista == "agregado":
        df_top_graf = (
            df_items_year
            .groupby(["Código", "Descripción corta"], as_index=False, observed=True)[metric_col]
            .sum()
            .rename(columns={metric_col: "Valor"})
            .sort_values("Valor", ascending=False)
            .head(20)
        )
        order_y = df_top_graf.sort_values("Valor", ascending=False)["Descripción corta"].tolist()
        fig = px.bar(
            df_top_graf,
            x="Valor",
            y="Descripción corta",
            orientation="h",
            title=None,
            labels={"Valor": ("Monto (Millones)" if medida == "monto" else "Cantidad"), "Descripción corta": "Insumo"},
            category_orders={"Descripción corta": order_y}
        )
        # Asegurar visibilidad de todas las etiquetas del eje Y
        fig.update_layout(height=max(520, 26 * len(order_y) + 100), margin=dict(l=220, r=20, t=60, b=40))
        fig.update_yaxes(automargin=True, tickmode="array", tickvals=order_y, ticktext=order_y, tickfont=dict(size=11))
    else:
        # Obtener Top 20 insumos por total agregado para ordenar correctamente
        df_agg_items = (
            df_items_year
            .groupby(["Código", "Descripción corta"], as_index=False, observed=True)[metric_col]
            .sum()
            .rename(columns={metric_col: "TotalItem"})
            .sort_values("TotalItem", ascending=False)
            .head(20)
        )
        top_keys = set(zip(df_agg_items["Código"], df_agg_items["Descripción corta"]))
        # Detalle por licitante solo para esos Top 20 insumos
        df_detail = (
            df_items_year
            .groupby(["Código", "Descripción corta", "Licitante"], as_index=False, observed=True)[metric_col]
            .sum()
            .rename(columns={metric_col: "Valor"})
        )
        df_detail = df_detail[df_detail.apply(lambda r: (r["Código"], r["Descripción corta"]) in top_keys, axis=1)]
        order_y = df_agg_items["Descripción corta"].tolist()  # orden descendente por total
        fig = px.bar(
            df_detail,
            x="Valor",
            y="Descripción corta",
            color="Licitante",
            orientation="h",
            title=None,
            labels={"Valor": ("Monto (Millones)" if medida == "monto" else "Cantidad"), "Descripción corta": "Insumo", "Licitante": "Licitante"},
            category_orders={"Descripción corta": order_y}
        )
        fig.update_layout(barmode='stack')
        # Asegurar visibilidad de todas las etiquetas del eje Y
        fig.update_layout(height=max(520, 26 * len(order_y) + 100), margin=dict(l=220, r=20, t=60, b=40))
        fig.update_yaxes(automargin=True, tickmode="array", tickvals=order_y, ticktext=order_y, tickfont=dict(size=11))
        # Evitar solapamiento: no mostrar etiquetas por segmento; solo mostrar etiqueta del total con una traza de texto
        fig.update_traces(texttemplate=None, selector=dict(type='bar'))
        # Totales por insumo para ubicar texto a la derecha
        df_tot = df_detail.groupby("Descripción corta", as_index=False)["Valor"].sum()
        totals_map = {k: v for k, v in zip(df_tot["Descripción corta"], df_tot["Valor"])}
        x_totals = [float(totals_map.get(y, 0.0) or 0.0) for y in order_y]
        # Formateo del texto de totales
        if medida == "monto":
            text_totals = [format_mill_int(v) for v in x_totals]
        else:
            text_totals = [f"{int(round(v)):,}".replace(",", ".") for v in x_totals]
        # Margen extra en X para que entre el texto
        max_total = max(x_totals) if x_totals else 0.0
        if max_total > 0:
            fig.update_xaxes(range=[0, max_total * 1.08])
        # Agregar traza de texto superpuesta (scatter) con los totales
        fig.add_trace(
            go.Scatter(
                x=x_totals,
                y=order_y,
                mode="text",
                text=text_totals,
                textposition="middle right",
                showlegend=False,
                hoverinfo="skip",
            )
        )
        # Ocultar textos que no entren
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode="hide")

    # Formato de hover/text según medida
    # Formato de hover/text según medida (agregado: etiquetas por barra; detalle: solo hover por segmento)
    if vista == "agregado":
        if medida == "monto":
            fig.update_traces(hovertemplate="Insumo=%{y}<br>Monto=%{x:.0f}M", texttemplate="%{x:.0f}M", textposition="outside", cliponaxis=False)
        else:
            fig.update_traces(hovertemplate="Insumo=%{y}<br>Cantidad=%{x:.0f}", texttemplate="%{x:.0f}", textposition="outside", cliponaxis=False)
    else:
        # detalle: mantener hover detallado por licitante y sin texto en segmentos (ya se agregó traza de totales)
        if medida == "monto":
            fig.update_traces(hovertemplate="Insumo=%{y}<br>Licitante=%{legendgroup}<br>Monto=%{x:.0f}M")
        else:
            fig.update_traces(hovertemplate="Insumo=%{y}<br>Licitante=%{legendgroup}<br>Cantidad=%{x:.0f}")

    # Textos explicativos
    if vista == "agregado":
        explicacion_tabla = html.Small(
            ("Esta tabla lista el Top 20 de ítems " + ("por monto (M)" if medida == "monto" else "por cantidad") + " agregados por ítem en el año seleccionado."),
            className="text-muted"
        )
        explicacion_grafico = html.Small(
            ("Este gráfico agrega por ítem (suma de todos los licitantes) y muestra los 20 ítems con mayor " + ("monto (M)" if medida == "monto" else "cantidad") + "."),
            className="text-muted"
        )
        titulo_tabla = html.H5(f"Top 20 insumos por {'monto' if medida=='monto' else 'cantidad'} (agregado)")
        titulo_grafico = None
    else:
        explicacion_tabla = html.Small(
            ("Esta tabla lista el Top 20 de combinaciones Ítem–Licitante " + ("por monto (M)" if medida == "monto" else "por cantidad") + "."),
            className="text-muted"
        )
        explicacion_grafico = html.Small(
            ("Este gráfico muestra el Top 20 en detalle por licitante. El color identifica a cada licitante."),
            className="text-muted"
        )
        titulo_tabla = html.H5(f"Top 20 insumos contratados por {'monto' if medida=='monto' else 'cantidad'} (detalle por licitante)")
        titulo_grafico = None

    # Mensaje si la métrica es toda cero (p. ej. cantidades ausentes)
    info_extra = None
    if df_top_tabla["Valor"].sum() == 0:
        info_extra = html.Div(html.Small("No hay cantidades/montos distintos de cero para este año en la selección actual.", className="text-warning"))

    # Armar bloques sin título duplicado para el gráfico
    bloques = [titulo_tabla, tabla, explicacion_tabla, dcc.Graph(figure=fig), explicacion_grafico]
    if info_extra:
        bloques.append(info_extra)
    return html.Div(bloques)

# ------------------------------------------------------
# Página PROCESOS FILTRADOS (filtros y tabla)
# ------------------------------------------------------
def layout_procesos():
    """Genera el layout de la página de "Procesos Filtrados" con filtros.

    Retorna
    -------
    dash.html.Div
        Contenedor con filtros y la tabla de resultados.
    """
    años = sorted(df["año"].dropna().unique())
    compradores = sorted([x for x in df["licitante"].dropna().unique()])
    proveedores = sorted([x for x in df["proveedor"].dropna().unique()])
    tipos = sorted([x for x in df["tipo_contratacion"].dropna().unique()])
    mapping_tipos = {
        "CDI": "Contratación Directa (CDI)",
        "LPU": "Licitación Pública (LPU)"
    }

    # Definir columnas para el DataTable (visibles) con formato numérico
    columns_out = [
        {"name": "Fecha", "id": "fecha"},
        {"name": "Proceso", "id": "Proceso"},
        {"name": "Título", "id": "Título"},
        {"name": "Licitante", "id": "licitante"},
        {"name": "Proveedor", "id": "proveedor"},
        {"name": "Orden de Compra", "id": "Orden de Compra"},
        {
            "name": "Monto (Millones)",
            "id": "Monto (Millones)",
            "type": "numeric",
            "format": Format(
                scheme=Scheme.fixed,
                precision=0,
                group=Group.yes,
                groups=3
            ).group_delimiter('.')
             .decimal_delimiter(',')
             .symbol(Symbol.yes)
             .symbol_suffix('M')
        }
    ]

    return html.Div([
        html.H4("🔎 Procesos Filtrados"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="filtro-año", options=[{"label": str(a), "value": a} for a in años], value=(años[-1] if años else None), clearable=False, placeholder=("Sin datos" if not años else None)), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-comprador", options=[{"label": c, "value": c} for c in compradores], placeholder="Seleccionar comprador"), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-proveedor", options=[{"label": p, "value": p} for p in proveedores], placeholder="Seleccionar proveedor"), md=3),
            dbc.Col(
                dcc.Dropdown(
                    id="filtro-tipo",
                    options=[{"label": mapping_tipos.get(t, t), "value": t} for t in tipos],
                    placeholder="Seleccionar tipo"
                ),
                md=3
            )
        ], className="mb-3"),
        dash_table.DataTable(
            id="tabla-procesos-filter",
            columns=columns_out,
            data=[],
            style_table={"overflowX": "auto"},
            style_cell={"fontSize": "70%"},
            page_size=20,
            sort_action="custom",
            sort_mode="multi",
            sort_by=[]
        ),
        html.Hr(),
    ])

@app.callback(
    Output("tabla-procesos-filter", "data"),
    Input("filtro-año", "value"),
    Input("filtro-comprador", "value"),
    Input("filtro-proveedor", "value"),
    Input("filtro-tipo", "value"),
    Input("tabla-procesos-filter", "sort_by")
)
def filtrar_procesos(año, comprador, proveedor, tipo, sort_by):
    """Callback que filtra procesos por año, comprador, proveedor y tipo.

    Parámetros
    ----------
    año : int
        Año a filtrar.
    comprador : str | None
        Nombre del licitante (opcional).
    proveedor : str | None
        Nombre del proveedor (opcional).
    tipo : str | None
        Tipo de contratación, p. ej. ``"LPU"``, ``"CDI"`` (opcional).

    Retorna
    -------
    dash.dash_table.DataTable | dash.html.Div
        Tabla con resultados o mensaje si no hay coincidencias.
    """
    df_f = df[df["año"] == año].copy()
    if comprador:
        df_f = df_f[df_f["licitante"] == comprador]
    if proveedor:
        df_f = df_f[df_f["proveedor"] == proveedor]
    if tipo:
        df_f = df_f[df_f["tipo_contratacion"] == tipo]

    if año is None or df_f.empty:
        return []

    # Ya tenemos 'fecha_dt' precalculada y 'orden_compra' en df
    df_f["fecha"] = pd.to_datetime(df_f["fecha"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "orden_compra" in df_f.columns:
        df_f["Orden de Compra"] = df_f["orden_compra"]
    else:
        df_f["Orden de Compra"] = None

    # columna Proceso (tender_id), y formateamos monto para mostrar
    df_f = df_f.rename(columns={"tender_id": "Proceso", "titulo": "Título"})
    # Usamos valor numérico en millones para permitir ordenamiento nativo correcto (redondeado)
    df_f["Monto (Millones)"] = df_f["monto_millones"].round(0)

    cols = ["fecha", "Proceso", "Título", "licitante", "proveedor", "Orden de Compra", "Monto (Millones)"]
    # títulos de columnas con capitalización y espacio
    columns_out = [
        {"name": "Fecha", "id": "fecha"},
        {"name": "Proceso", "id": "Proceso"},
        {"name": "Título", "id": "Título"},
        {"name": "Licitante", "id": "licitante"},
        {"name": "Proveedor", "id": "proveedor"},
        {"name": "Orden de Compra", "id": "Orden de Compra"},
        {
            "name": "Monto (Millones)",
            "id": "Monto (Millones)",
            "type": "numeric",
            "format": Format(
                scheme=Scheme.fixed,
                precision=0,
                group=Group.yes,
                groups=3
            ).group_delimiter('.')
             .decimal_delimiter(',')
             .symbol(Symbol.yes)
             .symbol_suffix('M')
        }
    ]

    # Aplicar ordenamiento del lado del servidor si el usuario hizo click en encabezados
    if sort_by and isinstance(sort_by, list) and len(sort_by) > 0:
        # Mapear 'fecha' a la columna interna 'fecha_dt' para ordenar correctamente
        by = []
        ascending = []
        for s in sort_by:
            col = s.get("column_id")
            direction = s.get("direction", "asc")
            if col == "fecha":
                by.append("fecha_dt")
            else:
                by.append(col)
            ascending.append(direction == "asc")
        try:
            # mergesort para estabilidad cuando hay empates
            df_f = df_f.sort_values(by=by, ascending=ascending, kind="mergesort")
        except Exception:
            # Si algo falla, no interrumpimos la UI
            pass

    # Devolver solo los registros (data) en el orden aplicado
    return df_f[cols].to_dict("records")

# ------------------------------------------------------
# Página ACERCA DEL PROYECTO
# ------------------------------------------------------
def layout_acerca():
    return html.Div([
        html.H4("ℹ️ Acerca del proyecto"),
        html.P(
            "Este dashboard presenta visualizaciones y tablas construidas a partir de datos publicados bajo el estándar OCDS (Open Contracting Data Standard) para la Provincia de Mendoza.",
            style={"fontStyle": "italic"}
        ),
        html.Ul([
            html.Li([
                html.Strong("Autor: "),
                html.A("Ing. Leonardo Raúl Federico Villegas", href="https://github.com/Leonardorf", target="_blank"),
                html.Span(" · "),
                html.A("Perfil en GitHub", href="https://github.com/Leonardorf", target="_blank")
            ]),
            html.Li([
                html.Strong("Contacto: "),
                html.A("leonfevi@gmail.com", href="mailto:leonfevi@gmail.com")
            ]),
            html.Li([
                html.Strong("Documentación: "),
                html.A("GitHub Pages", href="https://leonardorf.github.io/contrataciones-publicas-OCDS/", target="_blank")
            ]),
            html.Li([
                html.Strong("Repositorio: "),
                html.A("Leonardorf/contrataciones-publicas-OCDS", href="https://github.com/Leonardorf/contrataciones-publicas-OCDS", target="_blank")
            ]),
            html.Li([
                html.Strong("Endpoints de servicio: "),
                html.Code("/health"), html.Span(" y "), html.Code("/reload-data")
            ]),
            html.Li([
                html.Strong("Fuente de datos: "),
                html.A("Portal de Datos Abiertos - Compras Mendoza", href="https://datosabiertos-compras.mendoza.gov.ar/", target="_blank")
            ]),
        ], style={"lineHeight": "1.8"}),
        html.Hr(),
        html.P(
            "Sugerencias y mejoras son bienvenidas a través de issues o PRs en el repositorio.",
            className="text-muted"
        )
    ])

# ------------------------------------------------------
# RUTAS
# ------------------------------------------------------
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def mostrar_pagina(pathname):
    if pathname in ("/", None):
        return layout_home()
    elif pathname and pathname.startswith("/insumos"):
        return layout_insumos()
    elif pathname and pathname.startswith("/procesos"):
        return layout_procesos()
    elif pathname and pathname.startswith("/acerca"):
        return layout_acerca()
    else:
        return html.H4("Página no encontrada.")

# ------------------------------------------------------
if __name__ == "__main__":
    # Permitir configurar host/port por entorno (útil para Codespaces/Paas)
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8050"))
    debug = os.getenv("DEBUG", "1") not in ("0", "false", "False")
    # Importante en local: desactivar el reloader para evitar doble proceso y estados globales inconsistentes
    app.run(host=host, port=port, debug=debug, use_reloader=False)

# ------------------------------------------------------
# Callbacks auxiliares para recarga de datos vía botón (cuando df vacío)
# ------------------------------------------------------
@app.callback(
    Output("reload-poller", "disabled"),
    Output("reload-status", "children"),
    Output("reload-done", "data"),
    Input("btn-reload-data", "n_clicks"),
    prevent_initial_call=True
)
def trigger_reload(n):
    if not n:
        raise dash.exceptions.PreventUpdate
    # Intento de recarga sin bloquear: usamos requests interno
    try:
        ensure_data_loaded(force=True)
        if len(df) == 0:
            return False, "Intentando recargar... aún sin filas.", None
        return True, f"Recarga completada. Filas: {len(df)}. Refresca el año o la página.", {"rows": len(df)}
    except Exception as e:
        return True, f"Error al recargar: {e}", None
