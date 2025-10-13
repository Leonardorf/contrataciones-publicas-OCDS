# app.py -- Versión 0.1.4 (corrección de formatos de monto en tablas)
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import json, re, os, requests

# ------------------------------------------------------
# CONFIGURACIÓN BASE
# ------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Contrataciones Públicas de Mendoza (OCDS)"
server = app.server

# ------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------
def cargar_ocds(ruta):
    if ruta.startswith("http"):
        resp = requests.get(ruta)
        resp.raise_for_status()
        return resp.json()
    elif os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError(f"No se reconoce la ruta: {ruta}")

def extraer_contratos(data):
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
                        "submission_details": submission_details
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
                    "submission_details": submission_details
                })

    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["año"] = df["fecha"].dt.year
    return df

def detectar_tipo(tender_id, titulo=None, contrato_desc=None, submission_details=None):
    """
    Detecta LPU / CDI u Otro a partir de:
     - tender_id (busca '-XXX99' al final)
     - o, si no existe, infiere desde título o submission_details o description
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
    """
    Formatea números en millones para tablas:
    - toma un valor numérico que representa 'millones' (por ejemplo 54137.6)
    - redondea al entero: 54137
    - devuelve string con '.' como separador de miles y sufijo 'M' -> '54.137M'
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
    """Formato para hover en gráficos: '54.137M' pero con decimales (54.137.600 -> 54137.600 -> 54137.600 M)"""
    if pd.isna(x):
        return "-"
    val = float(x)
    # mostramos con 3 decimales (ej: 54137.600) y añadimos 'M'
    return f"{val:,.3f}".replace(",", ".") + "M"

# ------------------------------------------------------
# CARGA DE DATOS y normalizaciones
# ------------------------------------------------------
URL_JSON = r"C:\Users\Leonardo Villegas\Downloads\20250810_release.json"
data = cargar_ocds(URL_JSON)
df = extraer_contratos(data)

# Añadimos tipo (intento por tender_id, con fallback a título/descr)
df["tipo_contratacion"] = df.apply(
    lambda r: detectar_tipo(r.get("tender_id"), r.get("titulo"), r.get("contrato_desc"), r.get("submission_details")),
    axis=1
)

# convertimos monto a float y creamos columna en millones (numérica)
df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0.0)
df["monto_millones"] = df["monto"] / 1_000_000.0

# ------------------------------------------------------
# LAYOUT BASE
# ------------------------------------------------------
app.layout = dbc.Container([
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("🏠 Home", href="/", active="exact")),
            dbc.NavItem(dbc.NavLink("🏷️ Insumos", href="/insumos", active="exact")),
            dbc.NavItem(dbc.NavLink("🔎 Procesos filtrados", href="/procesos", active="exact")),
        ],
        brand="📊 Contrataciones Mendoza (OCDS)",
        color="primary",
        dark=True,
        className="mb-4"
    ),
    dcc.Location(id="url"),
    html.Div(id="page-content"),
], fluid=True)

# ------------------------------------------------------
# Página HOME
# ------------------------------------------------------
def layout_home():
    años = sorted(df["año"].dropna().unique())
    año_sel = años[-1] if años else None
    rango = f"{df['fecha'].min().date()} → {df['fecha'].max().date()}"
    return html.Div([
        html.H5(f"📅 Rango de fechas detectado: {rango}"),
        html.P(
            "OCDS (Open Contracting Data Standard) es un estándar para publicar datos de contrataciones públicas "
            "en formato uniforme. Usarlo ayuda a comparar, analizar y auditar los procesos de compra pública.",
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
        html.P("Versión 0.1.4 – Dashboard OCDS Mendoza", className="text-muted small text-end")
    ])

@app.callback(Output("contenido-home", "children"), Input("año-selector-home", "value"))
def actualizar_home(año_sel):
    if año_sel is None:
        return html.Div("No hay datos disponibles.")
    df_f = df[df["año"] == año_sel].copy()

    # --- Totales por tipo (numérico) y versión para mostrar formateada ---
    totales = df_f.groupby("tipo_contratacion", as_index=False)["monto_millones"].sum()
    # mantenemos la columna numérica para cálculos y generamos columna formateada para mostrar
    totales["Monto (Millones)"] = totales["monto_millones"].apply(format_mill_int)
    totales_display = totales[["tipo_contratacion", "Monto (Millones)"]].rename(columns={"tipo_contratacion": "Tipo Contratación"})

    tabla_totales = dash_table.DataTable(
        id="tabla-totales",
        columns=[{"name": c, "id": c} for c in totales_display.columns],
        data=totales_display.to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=10
    )

    # --- Evolución mensual (gráfico) ---
    df_mes = df_f.groupby(df_f["fecha"].dt.month, as_index=False).agg(total_monto=("monto_millones", "sum")).rename(columns={"fecha": "mes"})
    # df_mes columns: first column is month (named 'fecha' by grouping index previously) - rename properly:
    if "fecha" in df_mes.columns:
        df_mes = df_mes.rename(columns={"fecha": "mes"})
    # ensure we have column 'mes' (month number)
    if "mes" not in df_mes.columns:
        # fallback - build month
        df_mes = df_f.assign(mes=df_f["fecha"].dt.month).groupby("mes", as_index=False).agg(total_monto=("monto_millones", "sum"))

    fig_mes = px.line(df_mes, x="mes", y="total_monto", title=f"Evolución mensual ({año_sel})",
                      labels={"mes": "Mes", "total_monto": "Monto (Millones)"})
    # hover con 3 decimales en M
    fig_mes.update_traces(hovertemplate="Mes=%{x}<br>Monto=%{y:.3f}M")

    # --- Top 10 licitantes (año) ---
    top10 = df_f.groupby("licitante", as_index=False)["monto_millones"].sum().nlargest(10, "monto_millones")
    fig_top10 = px.bar(top10, x="monto_millones", y="licitante", orientation="h",
                       title=f"Top 10 Licitantes ({año_sel})",
                       labels={"monto_millones": "Monto (Millones)", "licitante": "Licitante"})
    fig_top10.update_traces(hovertemplate="Licitante=%{y}<br>Monto=%{x:.3f}M")

    # --- Top 20 licitantes (total) ---
    top20 = df.groupby("licitante", as_index=False)["monto_millones"].sum().nlargest(20, "monto_millones")
    fig_top20 = px.bar(top20, x="monto_millones", y="licitante", orientation="h",
                       title="Top 20 Licitantes (Total)",
                       labels={"monto_millones": "Monto (Millones)", "licitante": "Licitante"})
    fig_top20.update_traces(hovertemplate="Licitante=%{y}<br>Monto=%{x:.3f}M")

    # --- Pie: monto por tipo ---
    dist_tipo = df_f.groupby("tipo_contratacion", as_index=False)["monto_millones"].sum()
    dist_tipo = dist_tipo[dist_tipo["monto_millones"] > 0]
    fig_pie = px.pie(dist_tipo, values="monto_millones", names="tipo_contratacion", title=f"Monto por tipo de contratación ({año_sel})")
    fig_pie.update_traces(hovertemplate="%{label}: %{value:.3f}M")

    # --- Top 30 montos (tabla) ---
    top30 = df_f.sort_values("monto", ascending=False).head(30).copy()
    # columnas y formato de vista
    top30["Monto (Millones)"] = top30["monto_millones"].apply(format_mill_int)
    top30["fecha"] = top30["fecha"].dt.strftime("%Y-%m-%d")
    top30 = top30.rename(columns={"tender_id": "Proceso", "titulo": "Título", "licitante": "Licitante", "proveedor": "Proveedor"})
    cols_top30 = ["fecha", "Proceso", "Título", "Licitante", "Proveedor", "Monto (Millones)"]
    tabla_top30 = dash_table.DataTable(
        id="tabla-top30",
        columns=[{"name": c, "id": c} for c in cols_top30],
        data=top30[cols_top30].to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=15,
        sort_action="native",
    )

    return html.Div([
        html.H4(f"💰 Total contratado por tipo de contratación ({año_sel})"),
        tabla_totales,
        dcc.Graph(figure=fig_mes),
        dcc.Graph(figure=fig_top10),
        dcc.Graph(figure=fig_top20),
        dcc.Graph(figure=fig_pie),
        html.H4(f"🏆 Top 30 Montos más altos ({año_sel})"),
        tabla_top30
    ])

# ------------------------------------------------------
# Página INSUMOS (se respeta formato de monto en 'M')
# ------------------------------------------------------
def layout_insumos():
    años = sorted(df["año"].dropna().unique())
    año_sel = años[-1] if años else None
    return html.Div([
        html.H4("🏷️ Top Insumos más contratados"),
        dcc.Dropdown(
            id="año-selector-insumos",
            options=[{"label": str(a), "value": a} for a in años],
            value=año_sel,
            clearable=False
        ),
        html.Div(id="contenido-insumos"),
        html.Hr(),
        html.P("Versión 0.1.4 – Dashboard OCDS Mendoza", className="text-muted small text-end")
    ])

@app.callback(Output("contenido-insumos", "children"), Input("año-selector-insumos", "value"))
def actualizar_insumos(año_sel):
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
    # formateamos M para mostrar
    df_top["Monto (Millones)"] = df_top["Monto (Millones)"].apply(format_mill_int)

    tabla = dash_table.DataTable(
        id="tabla-insumos",
        columns=[{"name": c, "id": c} for c in df_top.columns],
        data=df_top.to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=15,
        sort_action="native"
    )
    fig = px.bar(df_top, x="Monto (Millones)", y="Descripción corta", color="Licitante", orientation="h", title=f"Top 30 Insumos más contratados ({año_sel})")
    return html.Div([tabla, dcc.Graph(figure=fig)])

# ------------------------------------------------------
# Página PROCESOS FILTRADOS (filtros y tabla)
# ------------------------------------------------------
def layout_procesos():
    años = sorted(df["año"].dropna().unique())
    compradores = sorted([x for x in df["licitante"].dropna().unique()])
    proveedores = sorted([x for x in df["proveedor"].dropna().unique()])
    tipos = sorted([x for x in df["tipo_contratacion"].dropna().unique()])

    return html.Div([
        html.H4("🔎 Procesos filtrados"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="filtro-año", options=[{"label": str(a), "value": a} for a in años], value=años[-1], clearable=False), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-comprador", options=[{"label": c, "value": c} for c in compradores], placeholder="Seleccionar comprador"), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-proveedor", options=[{"label": p, "value": p} for p in proveedores], placeholder="Seleccionar proveedor"), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-tipo", options=[{"label": t, "value": t} for t in tipos], placeholder="Seleccionar tipo"), md=3)
        ], className="mb-3"),
        html.Div(id="tabla-procesos"),
        html.Hr(),
        html.P("Versión 0.1.4 – Dashboard OCDS Mendoza", className="text-muted small text-end")
    ])

@app.callback(
    Output("tabla-procesos", "children"),
    Input("filtro-año", "value"),
    Input("filtro-comprador", "value"),
    Input("filtro-proveedor", "value"),
    Input("filtro-tipo", "value")
)
def filtrar_procesos(año, comprador, proveedor, tipo):
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
    # columna Proceso (tender_id), y formateamos monto para mostrar
    df_f = df_f.rename(columns={"tender_id": "Proceso", "titulo": "Título"})
    df_f["Monto (Millones)"] = df_f["monto_millones"].apply(format_mill_int)

    cols = ["fecha", "Proceso", "Título", "licitante", "proveedor", "Monto (Millones)"]
    # títulos de columnas con capitalización y espacio
    columns_out = [
        {"name": "Fecha", "id": "fecha"},
        {"name": "Proceso", "id": "Proceso"},
        {"name": "Título", "id": "Título"},
        {"name": "Licitante", "id": "licitante"},
        {"name": "Proveedor", "id": "proveedor"},
        {"name": "Monto (Millones)", "id": "Monto (Millones)"}
    ]
    tabla = dash_table.DataTable(
        id="tabla-procesos-filter",
        columns=columns_out,
        data=df_f[["fecha", "Proceso", "Título", "licitante", "proveedor", "Monto (Millones)"]].to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=20,
        sort_action="native"
    )
    return tabla

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
    else:
        return html.H4("Página no encontrada.")

# ------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
