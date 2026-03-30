import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Dashboard Métricas Quejas", layout="wide")

st.title("📊 Dashboard Métricas de Quejas")
st.markdown("""
Este dashboard interactivo muestra las métricas calculadas a partir del archivo `outputs/metricas_resumen.xlsx`. Si el archivo cambia, el dashboard se actualizará automáticamente al recargar la página.
""")

# Ruta al archivo de métricas
METRICAS_PATH = os.path.join("outputs", "metricas_resumen.xlsx")

# Cargar datos
@st.cache_data(show_spinner=False)
def load_data():
    return pd.read_excel(METRICAS_PATH)

df = load_data()

# Mostrar tabla
st.subheader("Vista general de métricas")
st.dataframe(df, use_container_width=True)

# Selección de columna para análisis
cols = [col for col in df.columns if df[col].dtype != 'O']
if cols:
    col_sel = st.selectbox("Selecciona una métrica para graficar:", cols)
    fig = px.histogram(df, x=col_sel, nbins=20, title=f"Distribución de {col_sel}")
    st.plotly_chart(fig, use_container_width=True)

# Filtros dinámicos
with st.expander("Filtrar por valores", expanded=False):
    for col in df.select_dtypes(include='object').columns:
        vals = df[col].unique().tolist()
        sel = st.multiselect(f"Filtrar {col}", vals, default=vals)
        df = df[df[col].isin(sel)]

    st.write(f"Filas después del filtro: {len(df)}")

# Mostrar tabla filtrada
st.dataframe(df, use_container_width=True)
