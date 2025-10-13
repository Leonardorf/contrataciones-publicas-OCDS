import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import json, os, re, requests

# ===================
# 1) Configuración base
# ===================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# -------------------
# Funciones (reutilizamos tu lógica)
# -------------------
def cargar_ocds(ruta):
    if ruta.startswith("http://") or ruta.startswith("https://"):
        resp = requests.get(ruta)
        resp.raise_for_status()
        return resp.json()
    elif os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError(f"No se reconoce la ruta: {ruta}")

def extraer_contratos(data):
    releases = data.get("releases", [])
    registros = []
    for rel in releases:
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
        for aw in awards:
            monto = aw.get("value", {}).get("amount")
            moneda = aw.get("value", {}).get("currency")
            estado_award = aw.get("status")
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
                        "estado_award": estado_award,
                    })
    df = pd.DataFrame(registros)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["año"] = df["fecha"].dt.year
    return df

# Cargar datos de ejemplo
URL_JSON = r"C:\Users\Leonardo Villegas\Downloads\20250810_release.json"
data = cargar_ocds(URL_JSON)
df = extraer_contratos(data)

# ===================
# 2) Layout con sidebar de filtros
# ===================
app.layout = dbc.Container([
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.H4("Filtros", className="mb-3"),
            dcc.Dropdown(
                id="filtro-comprador",
                options=[{"label": c, "value": c} for c in sorted(df["licitante"].dropna().unique())],
                placeholder="Seleccionar comprador",
                multi=True
            ),
            dcc.Dropdown(
                id="filtro-proveedor",
                options=[{"label": p, "value": p} for p in sorted(df["proveedor"].dropna().unique())],
                placeholder="Seleccionar proveedor",
                multi=True
            ),
            dcc.Dropdown(
                id="filtro-tipo",
                options=[{"label": t, "value": t} for t in df["estado_award"].dropna().unique()],
                placeholder="Estado del contrato",
                multi=True
            ),
            dcc.RangeSlider(
                id="filtro-monto",
                min=0,
                max=df["monto"].max(),
                step=1000000,
                value=[0, df["monto"].max()],
                tooltip={"placement": "bottom", "always_visible": True}
            ),
            dcc.Dropdown(
                id="filtro-anio",
                options=[{"label": int(a), "value": int(a)} for a in sorted(df["año"].dropna().unique())],
                placeholder="Seleccionar año",
                value=int(df["año"].max())
            ),
        ], width=3, style={"backgroundColor": "#f8f9fa", "padding": "15px"}),

        # Contenido principal
        dbc.Col([
            html.H3("📊 Contrataciones Públicas de Mendoza"),
            dcc.Graph(id="grafico-evolucion"),
            dcc.Graph(id="grafico-top10")
        ], width=9)
    ])
], fluid=True)

# ===================
# 3) Callbacks de filtros
# ===================
@app.callback(
    [Output("grafico-evolucion", "figure"),
     Output("grafico-top10", "figure")],
    [Input("filtro-comprador", "value"),
     Input("filtro-proveedor", "value"),
     Input("filtro-tipo", "value"),
     Input("filtro-monto", "value"),
     Input("filtro-anio", "value")]
)
def actualizar_graficos(fcomprador, fproveedor, ftipo, fmonto, fanio):
    df_filtrado = df.copy()

    if fanio:
        df_filtrado = df_filtrado[df_filtrado["año"] == fanio]
    if fcomprador:
        df_filtrado = df_filtrado[df_filtrado["licitante"].isin(fcomprador)]
    if fproveedor:
        df_filtrado = df_filtrado[df_filtrado["proveedor"].isin(fproveedor)]
    if ftipo:
        df_filtrado = df_filtrado[df_filtrado["estado_award"].isin(ftipo)]
    if fmonto:
        df_filtrado = df_filtrado[(df_filtrado["monto"] >= fmonto[0]) & (df_filtrado["monto"] <= fmonto[1])]

    # Gráfico evolución mensual
    df_mes = df_filtrado.groupby(df_filtrado["fecha"].dt.month).agg(total=("monto","sum")).reset_index()
    fig_evol = px.line(df_mes, x="fecha", y="total", title="Evolución mensual")
    fig_evol.update_layout(yaxis_tickformat=",.0f")

    # Top 10 licitantes
    top10 = df_filtrado.groupby("licitante")["monto"].sum().nlargest(10).reset_index()
    fig_top10 = px.bar(top10, x="monto", y="licitante", orientation="h", title="Top 10 Licitantes")
    fig_top10.update_layout(xaxis_tickformat=",.0f")

    return fig_evol, fig_top10

# ===================
# 4) Ejecutar
# ===================
if __name__ == "__main__":
    app.run(debug=True)
