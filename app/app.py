# Revertimos a la versión 0.1.4 manteniendo las mejoras en los tooltips
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import json, re, os, requests, threading
import flask

# Habilitar logs detallados para Flask
import logging
# Configurar logs para que se muestren en la terminal
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

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

        for aw in awards:
            monto = aw.get("value", {}).get("amount")
            moneda = aw.get("value", {}).get("currency")
            suppliers = aw.get("suppliers", [])
            if suppliers:
                for sup in suppliers:
                    registros.append({
                        "fecha": fecha,
                        "tender_id": tender_id,
                        "titulo": tender.get("title"),
                        "licitante": buyer.get("name"),
                        "proveedor": sup.get("name"),
                        "monto": monto,
                        "moneda": moneda,
                        "contracts": contracts,
                        "items": tender.get("items", []),
                        "contrato_desc": contrato_desc,
                        "submission_details": submission_details,
                        "awards": awards
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
                    "contracts": contracts,
                    "items": tender.get("items", []),
                    "contrato_desc": contrato_desc,
                    "submission_details": submission_details,
                    "awards": awards
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
_DATA_LOADED = False
_DATA_LOCK = threading.Lock()
_DATA_ERROR = None

def _cargar_datos_internamente(max_retries: int = 3, base_delay: float = 2.0):
    global data, df, _DATA_LOADED, _DATA_ERROR
    logging.info("Iniciando carga de datos OCDS desde %s", URL_JSON)
    last_err = None
    for intento in range(1, max_retries + 1):
        try:
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
    df_local = extraer_contratos(raw)
    if not df_local.empty:
        df_local["tipo_contratacion"] = df_local.apply(
            lambda r: detectar_tipo(r.get("tender_id"), r.get("titulo"), r.get("contrato_desc"), r.get("submission_details")),
            axis=1
        )
        df_local["monto"] = pd.to_numeric(df_local["monto"], errors="coerce").fillna(0.0)
        df_local["monto_millones"] = df_local["monto"] / 1_000_000.0
    data = raw
    df = df_local
    _DATA_LOADED = True
    _DATA_ERROR = None
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
        return flask.jsonify(message="Modo SPHINX_BUILD: no se carga dataset"), 200
    ensure_data_loaded(force=True)
    if _DATA_ERROR:
        return flask.jsonify(status="error", error=_DATA_ERROR), 500
    return flask.jsonify(status="ok", rows=len(df)), 200

# ------------------------------------------------------
# ENCABEZADO CON ESCUDO
# ------------------------------------------------------
header = dbc.Navbar(
    dbc.Container([
        html.A(
            html.Img(
                src="https://mza-dicaws-portal-uploads-media-prod.s3.amazonaws.com/principal/uploads/2025/10/SITIO-AC_200x200-1-300x300-1.png",
                style={"height": "80px"}  # Ajustamos el tamaño
            ),
            href="https://www.mendoza.gov.ar/compras/",  # Hipervínculo al escudo de gobierno
            target="_blank"  # Abrir en una nueva pestaña
        ),
        html.H1([
            "Dashboard de Contrataciones Públicas de Mendoza (OCDS)          ",
            html.A(
                html.Img(
                    src="https://ocp.imgix.net/wp-content/uploads/2020/01/OCDS-logo-grey.png?auto=format&w=1800",
                    style={
                        "height": "50px",
                        "marginLeft": "100px",
                        "backgroundColor": "white",  # Fondo blanco
                        "padding": "5px",  # Espaciado interno
                        "borderRadius": "5px"  # Bordes redondeados
                    }
                ),
                href="https://www.open-contracting.org/",  # Hipervínculo a Open Contracting
                target="_blank"  # Abrir en una nueva pestaña
            )
        ], className="text-center text-white", style={"marginLeft": "-100%"}),  # Ajustamos el margen para centrar mejor
    ]),
    color="dark",
    dark=True,
    className="mb-4"
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
            dbc.NavItem(dbc.NavLink("🔎 Procesos Filtrados", href="/procesos", active="exact")),
            dbc.NavItem(dbc.NavLink("ℹ️ Acerca del proyecto", href="/acerca", active="exact")),
            dbc.NavItem(dbc.NavLink("📖 Documentación", href="https://leonardorf.github.io/contrataciones-publicas-OCDS/", target="_blank")),
        ],
        brand=[
            "📊 Dashboard de Contrataciones Públicas de Mendoza (OCDS)",
            html.Img(
                src="https://mza-dicaws-portal-uploads-media-prod.s3.amazonaws.com/principal/uploads/2025/10/SITIO-AC_200x200-1-300x300-1.png",
                style={"height": "50px", "marginRight": "10px"}  # Ajustamos el tamaño y el margen
            ),
            html.Img(
                src="https://ocp.imgix.net/wp-content/uploads/2020/01/OCDS-logo-grey.png?auto=format&w=1800",
                style={"height": "50px", "marginLeft": "10px", "backgroundColor": "white",
                     
                    "borderRadius": "5px"  }  # Ajustamos el tamaño y el margen
            )
        ],
        color="primary",
        dark=True,
        className="mb-4"
    ),
    dcc.Location(id="url"),
    dcc.Store(id="reload-done"),
    html.Div(id="page-content"),
    html.P("Versión 0.1.5 – Dashboard OCDS Mendoza", className="text-muted small text-end")
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
    rango = f"{df['fecha'].min().date()} → {df['fecha'].max().date()}"
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
    totales["tipo_contratacion_ext"] = totales["tipo_contratacion"].map(mapping_tipos).fillna(totales["tipo_contratacion"])  # fallback a valor original
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
    dist_tipo["tipo_contratacion_ext"] = dist_tipo["tipo_contratacion"].map(mapping_tipos).fillna(dist_tipo["tipo_contratacion"])
    fig_pie = px.pie(dist_tipo, values="monto_millones", names="tipo_contratacion_ext", title=capitalize_title(f"Monto por tipo de contratación ({año_sel})"))
    fig_pie.update_traces(hovertemplate="%{label}: %{value:.0f}M")

    # --- Top 10 licitantes (año) ---
    top10 = df_f.groupby("licitante", as_index=False)["monto_millones"].sum().nlargest(10, "monto_millones")
    fig_top10 = px.bar(top10, x="monto_millones", y="licitante", orientation="h",
                       title=capitalize_title(f"Top 10 Licitantes ({año_sel})"),
                       labels={"monto_millones": "Monto (Millones)", "licitante": "Licitante"})
    fig_top10.update_traces(hovertemplate="Licitante=%{y}<br>Monto=%{x:.0f}M")

    # --- Top 20 licitantes (total) ---
    top20 = df.groupby("licitante", as_index=False)["monto_millones"].sum().nlargest(20, "monto_millones")
    fig_top20 = px.bar(top20, x="monto_millones", y="licitante", orientation="h",
                       title=capitalize_title("Top 20 Licitantes (Total)"),
                       labels={"monto_millones": "Monto (Millones)", "licitante": "Licitante"})
    fig_top20.update_traces(hovertemplate="Licitante=%{y}<br>Monto=%{x:.0f}M")

    # --- Top 30 montos (tabla) ---
    top30 = df_f.sort_values("monto", ascending=False).head(30).copy()
    top30["Monto (Millones)"] = top30["monto_millones"].apply(format_mill_int)
    top30["fecha"] = top30["fecha"].dt.strftime("%Y-%m-%d")
    top30 = top30.rename(columns={"tender_id": "Proceso", "titulo": "Título", "licitante": "Licitante", "proveedor": "Proveedor"})
    cols_top30 = ["fecha", "Proceso", "Título", "Licitante", "Proveedor", "Monto (Millones)"]
    tabla_top30 = dash_table.DataTable(
        id="tabla-top30",
        columns=[{"name": c, "id": c} for c in cols_top30],
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
        html.Div(id="contenido-insumos"),
        html.Hr()
    ])

@app.callback(Output("contenido-insumos", "children"), Input("año-selector-insumos", "value"))
def actualizar_insumos(año_sel):
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
    df_f = df[df["año"] == año_sel]
    items = []
    for _, row in df_f.iterrows():
        for it in row.get("items", []):
            codigo = it.get("classification", {}).get("id") or it.get("id")
            descripcion = it.get("description")
            if codigo and descripcion:
                items.append({
                    "Código": codigo,
                    "Descripción corta": descripcion[:80],
                    "Licitante": row.get("licitante"),
                    "Monto (Millones)": row.get("monto_millones", 0)
                })
    if not items:
        return html.Div("⚠️ No se encontraron items para este año.")
    df_items = pd.DataFrame(items)
    df_top = df_items.groupby(["Código", "Descripción corta", "Licitante"], as_index=False)["Monto (Millones)"].sum().sort_values("Monto (Millones)", ascending=False).head(30)
    df_top["Monto (Millones)"] = df_top["Monto (Millones)"].apply(format_mill_int)

    tabla = dash_table.DataTable(
        id="tabla-insumos",
        columns=[{"name": c, "id": c} for c in df_top.columns],
        data=df_top.to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=15,
        sort_action="native"
    )
    fig = px.bar(df_top, x="Monto (Millones)", y="Descripción corta", color="Licitante", orientation="h", title=capitalize_title(f"Top 30 Insumos Más Contratados ({año_sel})"))
    fig.update_traces(hovertemplate="Descripción=%{y}<br>Monto=%{x}")

    return html.Div([tabla, dcc.Graph(figure=fig)])

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

    return html.Div([
        html.H4("🔎 Procesos Filtrados"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="filtro-año", options=[{"label": str(a), "value": a} for a in años], value=años[-1], clearable=False), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-comprador", options=[{"label": c, "value": c} for c in compradores], placeholder="Seleccionar comprador"), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-proveedor", options=[{"label": p, "value": p} for p in proveedores], placeholder="Seleccionar proveedor"), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-tipo", options=[{"label": t, "value": t} for t in tipos], placeholder="Seleccionar tipo"), md=3)
        ], className="mb-3"),
        html.Div(id="tabla-procesos"),
        html.Hr(),
    ])

@app.callback(
    Output("tabla-procesos", "children"),
    Input("filtro-año", "value"),
    Input("filtro-comprador", "value"),
    Input("filtro-proveedor", "value"),
    Input("filtro-tipo", "value")
)
def filtrar_procesos(año, comprador, proveedor, tipo):
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

    if df_f.empty:
        return html.Div("⚠️ No se encontraron procesos con esos filtros.")

    df_f["fecha"] = df_f["fecha"].dt.strftime("%Y-%m-%d")
    # Ajustamos la lógica para buscar el award correspondiente al proveedor y luego el contrato
    def obtener_orden_compra(awards, contracts, proveedor):
        if not awards or not contracts:
            return None
        # Buscar el award que coincida con el proveedor
        for award in awards:
            if award.get("suppliers"):
                for supplier in award["suppliers"]:
                    if supplier.get("name") == proveedor:
                        # Buscar el contrato correspondiente al award
                        award_id = award.get("id")
                        for contract in contracts:
                            if contract.get("awardID") == award_id:
                                return contract.get("id")
        return None

    df_f["Orden de Compra"] = df_f.apply(lambda row: obtener_orden_compra(row.get("awards"), row.get("contracts"), row.get("proveedor")), axis=1)

    # columna Proceso (tender_id), y formateamos monto para mostrar
    df_f = df_f.rename(columns={"tender_id": "Proceso", "titulo": "Título"})
    df_f["Monto (Millones)"] = df_f["monto_millones"].apply(format_mill_int)

    # Añadimos una columna auxiliar para el ordenamiento correcto
    df_f["Monto (Millones) Orden"] = df_f["monto_millones"]

    cols = ["fecha", "Proceso", "Título", "licitante", "proveedor", "Orden de Compra", "Monto (Millones)"]
    # títulos de columnas con capitalización y espacio
    columns_out = [
        {"name": "Fecha", "id": "fecha"},
        {"name": "Proceso", "id": "Proceso"},
        {"name": "Título", "id": "Título"},
        {"name": "Licitante", "id": "licitante"},
        {"name": "Proveedor", "id": "proveedor"},
        {"name": "Orden de Compra", "id": "Orden de Compra"},
        {"name": "Monto (Millones)", "id": "Monto (Millones)", "type": "numeric"}
    ]

    # Incluimos la columna auxiliar en los datos pero no en las columnas visibles
    tabla = dash_table.DataTable(
        id="tabla-procesos-filter",
        columns=columns_out,  # Solo las columnas visibles
        data=df_f[cols + ["Monto (Millones) Orden"]].to_dict("records"),  # Incluimos la columna auxiliar
        style_table={"overflowX": "auto"},
        style_cell={"fontSize": "70%"},  # Reducir el tamaño de la fuente al 70%
        page_size=20,
        sort_action="native",
        sort_mode="multi"
    )
    return tabla

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
                html.A("Ing. Leonardo Villegas", href="https://github.com/Leonardorf", target="_blank")
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
    if pathname == "/":
        return layout_home()
    elif pathname == "/insumos":
        return layout_insumos()
    elif pathname == "/procesos":
        return layout_procesos()
    elif pathname == "/acerca":
        return layout_acerca()
    else:
        return html.H4("Página no encontrada.")

# ------------------------------------------------------
if __name__ == "__main__":
    # Permitir configurar host/port por entorno (útil para Codespaces/Paas)
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8050"))
    app.run(host=host, port=port, debug=True)

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
