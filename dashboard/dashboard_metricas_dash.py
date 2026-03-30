import dash
from dash import dcc, html, dash_table, Input, Output
import pandas as pd
import plotly.express as px
import os

METRICAS_PATH = os.path.join("outputs", "metricas_resumen.xlsx")

def load_data():
    return pd.read_excel(METRICAS_PATH)

df = load_data()

app = dash.Dash(__name__)
app.title = "Dashboard Métricas Quejas"

app.layout = html.Div([
    html.H1("📊 Dashboard Métricas de Quejas"),
    html.P("Este dashboard interactivo muestra las métricas calculadas a partir del archivo outputs/metricas_resumen.xlsx. Si el archivo cambia, el dashboard se actualizará al recargar la página."),
    dash_table.DataTable(
        id='tabla-metricas',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict('records'),
        page_size=15,
        filter_action="native",
        sort_action="native",
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'},
    ),
    html.Br(),
    html.Label("Selecciona una métrica numérica para graficar:"),
    dcc.Dropdown(
        id='columna-grafico',
        options=[{"label": col, "value": col} for col in df.select_dtypes(include='number').columns],
        value=df.select_dtypes(include='number').columns[0] if len(df.select_dtypes(include='number').columns) > 0 else None
    ),
    dcc.Graph(id='grafico-histograma'),
])

@app.callback(
    Output('grafico-histograma', 'figure'),
    Input('columna-grafico', 'value')
)
def actualizar_grafico(col):
    if col and col in df.columns:
        fig = px.histogram(df, x=col, nbins=20, title=f"Distribución de {col}")
        return fig
    return {}

if __name__ == "__main__":
    app.run_server(debug=True)
