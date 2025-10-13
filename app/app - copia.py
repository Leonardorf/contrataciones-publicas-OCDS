import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import json, re, os, requests

# ------------------------------------------------------
# Configuración base
# ------------------------------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Contrataciones Públicas de Mendoza (OCDS)"
server = app.server

# ------------------------------------------------------
# Funciones de carga y procesamiento
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
        tender_id = tender.get("id")
        contrato_desc = None
        if not tender_id and contracts:
            desc = contracts[0].get("description", "")
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
                        "items": tender.get("items", [])
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
                    "items": tender.get("items", [])
                })
    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["año"] = df["fecha"].dt.year
    return df

def detectar_tipo(tender_id):
    if pd.isna(tender_id):
        return "Otro"
    match = re.search(r"-([A-Z]+)\d+$", str(tender_id))
    return match.group(1) if match else "Otro"

# ------------------------------------------------------
# Cargar datos
# ------------------------------------------------------
URL_JSON = r"C:\Users\Leonardo Villegas\Downloads\20250810_release.json"
data = cargar_ocds(URL_JSON)
df = extraer_contratos(data)
df["tipo_contratacion"] = df["tender_id"].apply(detectar_tipo)
df["monto_millones"] = df["monto"] / 1_000_000

# ------------------------------------------------------
# Layout base
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
    html.Div(id="page-content")
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
        dcc.Dropdown(
            id="año-selector-home",
            options=[{"label": str(a), "value": a} for a in años],
            value=año_sel,
            clearable=False
        ),
        html.Div(id="contenido-home")
    ])

@app.callback(Output("contenido-home", "children"), Input("año-selector-home", "value"))
def actualizar_home(año_sel):
    if año_sel is None:
        return html.Div("No hay datos disponibles.")
    df_f = df[df["año"] == año_sel]

    # Totales
    totales = df_f.groupby("tipo_contratacion")["monto_millones"].sum().reset_index()
    tabla_totales = dash_table.DataTable(
        columns=[{"name": c.title(), "id": c} for c in totales.columns],
        data=totales.to_dict("records"),
        style_table={"overflowX": "auto"}
    )

    # Gráficos
    df_mes = df_f.groupby(df_f["fecha"].dt.month)["monto_millones"].sum().reset_index()
    fig_mes = px.line(df_mes, x="fecha", y="monto_millones", title="Evolución mensual")

    top10 = df_f.groupby("licitante")["monto_millones"].sum().nlargest(10).reset_index()
    fig_top10 = px.bar(top10, x="monto_millones", y="licitante", orientation="h", title="Top 10 Licitantes del año")

    top20 = df.groupby("licitante")["monto_millones"].sum().nlargest(20).reset_index()
    fig_top20 = px.bar(top20, x="monto_millones", y="licitante", orientation="h", title="Top 20 Licitantes total")

    dist_tipo = df_f.groupby("tipo_contratacion")["monto_millones"].sum().reset_index()
    fig_pie = px.pie(dist_tipo, values="monto_millones", names="tipo_contratacion", title="Monto por tipo de contratación")

    top30 = df_f.sort_values("monto", ascending=False).head(30).copy()
    top30["monto_millones"] = top30["monto_millones"].round(3)
    top30["monto_millones"] = top30["monto_millones"].apply(lambda x: f"{x:,.3f}".replace(",", ".") + "M")
    top30["fecha"] = top30["fecha"].dt.strftime("%Y-%m-%d")
    top30.rename(columns={"tender_id": "Proceso"}, inplace=True)

    tabla_top30 = dash_table.DataTable(
        columns=[{"name": c.title(), "id": c} for c in ["fecha", "Proceso", "titulo", "licitante", "proveedor", "monto_millones"]],
        data=top30[["fecha", "Proceso", "titulo", "licitante", "proveedor", "monto_millones"]].to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=15
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
# Página INSUMOS
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
        html.Div(id="contenido-insumos")
    ])

@app.callback(Output("contenido-insumos", "children"), Input("año-selector-insumos", "value"))
def actualizar_insumos(año_sel):
    df_f = df[df["año"] == año_sel]
    items = []
    for _, row in df_f.iterrows():
        for it in row.get("items", []):
            if it.get("description"):
                items.append({
                    "Código": it.get("classification", {}).get("id"),
                    "Descripción corta": it.get("description")[:80],
                    "Licitante": row["licitante"],
                    "Monto": row["monto_millones"]
                })
    if not items:
        return html.Div("⚠️ No se encontraron items para este año.")
    df_items = pd.DataFrame(items)
    df_top = df_items.groupby(["Código", "Descripción corta", "Licitante"], as_index=False)["Monto"].sum().sort_values("Monto", ascending=False).head(30)
    fig = px.bar(df_top, x="Monto", y="Descripción corta", color="Licitante", orientation="h", title=f"Top 30 Insumos más contratados ({año_sel})")

    tabla = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in df_top.columns],
        data=df_top.to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=15
    )
    return html.Div([tabla, dcc.Graph(figure=fig)])

# ------------------------------------------------------
# Página PROCESOS FILTRADOS
# ------------------------------------------------------
def layout_procesos():
    años = sorted(df["año"].dropna().unique())
    compradores = sorted(df["licitante"].dropna().unique())
    proveedores = sorted(df["proveedor"].dropna().unique())
    tipos = sorted(df["tipo_contratacion"].dropna().unique())

    return html.Div([
        html.H4("🔎 Procesos filtrados"),
        dbc.Row([
            dbc.Col(dcc.Dropdown(id="filtro-año", options=[{"label": str(a), "value": a} for a in años], value=años[-1], clearable=False), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-comprador", options=[{"label": c, "value": c} for c in compradores], placeholder="Seleccionar comprador"), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-proveedor", options=[{"label": p, "value": p} for p in proveedores], placeholder="Seleccionar proveedor"), md=3),
            dbc.Col(dcc.Dropdown(id="filtro-tipo", options=[{"label": t, "value": t} for t in tipos], placeholder="Seleccionar tipo"), md=3)
        ], className="mb-3"),
        html.Div(id="tabla-procesos")
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
    df_f["monto_millones"] = df_f["monto_millones"].round(3).apply(lambda x: f"{x:,.3f}".replace(",", ".") + "M")

    cols = ["fecha", "tender_id", "titulo", "licitante", "proveedor", "monto_millones"]
    df_f.rename(columns={"tender_id": "Proceso"}, inplace=True)
    tabla = dash_table.DataTable(
        columns=[{"name": c.title(), "id": c} for c in ["fecha", "Proceso", "titulo", "licitante", "proveedor", "monto_millones"]],
        data=df_f[["fecha", "Proceso", "titulo", "licitante", "proveedor", "monto_millones"]].to_dict("records"),
        style_table={"overflowX": "auto"},
        page_size=20
    )
    return tabla

# ------------------------------------------------------
# Controlador de rutas
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

