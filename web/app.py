import streamlit as st
import pandas as pd

# -----------------------------------
# Configuración de página
# -----------------------------------
st.set_page_config(
    page_title="Piloto E-Moviliza",
    layout="wide"
)

# -----------------------------------
# Cargar datos desde Excel
# -----------------------------------
@st.cache_data
def load_data():
    # Lee el archivo Excel (ruta relativa desde donde ejecutas Streamlit)
    df = pd.read_excel("web/totales.xlsx")

    # Ajusta los nombres de columnas según tu archivo
    df = df.rename(columns={
        '18/8/2025 al 19/09/2025': 'CLIENTE',  # primera columna con nombre de empresa
        'KG ': 'KG'                          # quitar espacio al final, si lo hubiera
    })

    return df

df = load_data()

st.title("Piloto E-Moviliza")
st.caption("Periodo del 18 de agosto de 2025 al 19 de septiembre de 2025")

# -----------------------------------
# Filtros en barra lateral (para indicadores y detalle)
# -----------------------------------
st.sidebar.header("Filtros")

clientes_disponibles = df["CLIENTE"].unique().tolist()

clientes_seleccionados = st.sidebar.multiselect(
    "Seleccionar empresa(s):",
    options=clientes_disponibles,
    default=clientes_disponibles  # por defecto todas
)

# Aplicar filtro SOLO para indicadores y detalle
if clientes_seleccionados:
    df_filtrado = df[df["CLIENTE"].isin(clientes_seleccionados)].copy()
else:
    df_filtrado = df.copy()

# -----------------------------------
# TOTALES GLOBALES (todas las empresas)
# -----------------------------------
total_km_global = df["TOTAL KM"].sum()
total_co2_global = df["CO2 EVITADO"].sum()
total_kg_global = df["KG"].sum()
total_horas_global = df["HORAS DE RUTA"].sum()
total_consumo_energ = df["KWH/KM"].sum()

st.subheader("Totales globales (todas las empresas)")

g1, g2, g3 = st.columns(3)
g4, g5 = st.columns(2)

with g1:
    st.metric("🚗 Total de km recorridos", f"{total_km_global:,.2f} km")

with g2:
    st.metric("🌱 CO₂ evitado", f"{total_co2_global:,.2f} kg CO₂ eq")

with g3:
    st.metric("📦 Total de carga transportada", f"{total_kg_global:,.2f} kg")

with g4:
    st.metric("⏱ Horas totales de ruta", f"{total_horas_global:,.2f} h")

with g5:
    st.metric("⚡ Consumo energético por Km", f"{total_consumo_energ:.3f} kWh/km")

st.markdown("---")

# -----------------------------------
# Tabla filtrada (empresas seleccionadas)
# -----------------------------------
st.subheader("Tabla por filtro (empresas seleccionadas)")
st.dataframe(df_filtrado.reset_index(drop=True), use_container_width=True)

st.markdown("---")

df_empresas_sel = (
    df_filtrado
    .groupby("CLIENTE")[["TOTAL KM", "CO2 EVITADO", "KG", "HORAS DE RUTA", "KWH/KM"]]
    .sum()
    .reset_index()
)

df_empresas_sel = df_empresas_sel.rename(columns={
    "TOTAL KM": "Km recorridos",
    "CO2 EVITADO": "CO₂ evitado (kg CO₂-eq)",
    "KG": "Kg transportados",
    "HORAS DE RUTA": "Horas de ruta",
    "KWH/KM": "Consumo energético por Km"
})

# -----------------------------------
# Gráficos rápidos (también con todas las empresas)
# -----------------------------------
st.subheader("Visualizaciones rápidas")

tab1, tab2, tab3, tab4, tab5= st.tabs(["Km recorridos por empresa", "CO₂ evitado por empresa","Kg transportados por empresa","Horas de ruta","Consumo energético por Km por empresa"])

with tab1:
    if not df_empresas_sel.empty:
        st.bar_chart(
            df_empresas_sel.set_index("CLIENTE")["Km recorridos"]
        )
    else:
        st.info("No hay datos para graficar.")

with tab2:
    if not df_empresas_sel.empty:
        st.bar_chart(
            df_empresas_sel.set_index("CLIENTE")["CO₂ evitado (kg CO₂-eq)"]
        )
    else:
        st.info("No hay datos para graficar.")

with tab3:
    if not df_empresas_sel.empty:
        st.bar_chart(
            df_empresas_sel.set_index("CLIENTE")["Kg transportados"]
        )
    else:
        st.info("No hay datos para graficar.")

with tab4:
    if not df_empresas_sel.empty:
        st.bar_chart(
            df_empresas_sel.set_index("CLIENTE")["Horas de ruta"]
        )
    else:
        st.info("No hay datos para graficar.")

with tab5:
    if not df_empresas_sel.empty:
        st.bar_chart(
            df_empresas_sel.set_index("CLIENTE")["Consumo energético por Km"]
        )
    else:
        st.info("No hay datos para graficar.")
