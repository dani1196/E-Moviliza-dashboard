import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="E-Moviliza | Tablero semanal", layout="wide")
st.markdown("""
<style>

/* =========================
   FONDO GENERAL
   ========================= */
.stApp {
    background: linear-gradient(180deg, #081B33 0%, #0B2545 100%);
    color: #F5F7FA;
}

/* Títulos */
h1, h2, h3 {
    color: #FFFFFF !important;
    font-weight: 800;
}

/* Texto normal */
p, span, label {
    color: #E6EAF0 !important;
}

/* =========================
   TARJETAS KPI
   ========================= */
.kpi-card{
    background: linear-gradient(145deg, #FFF3B0, #FFD23F);
    border-radius: 16px;
    padding: 18px 20px;
    box-shadow: 0 10px 22px rgba(0,0,0,0.35);
    transition: transform .12s ease, box-shadow .12s ease;
    min-height: 120px;
}

.kpi-card:hover{
    transform: translateY(-3px);
    box-shadow: 0 16px 32px rgba(0,0,0,0.45);
}

/* Encabezado KPI */
.kpi-top{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}

.kpi-label{
    font-size: 14px;
    font-weight: 700;
    color: #2B2100;
}

.kpi-icon{
    font-size: 22px;
}

/* Valor principal */
.kpi-value{
    font-size: 36px;
    font-weight: 900;
    color: #081B33;
    line-height: 1.1;
}

/* Texto pequeño */
.kpi-sub{
    margin-top: 4px;
    font-size: 12px;
    color: #3A2E00;
    opacity: 0.9;
}

/* =========================
   FILTROS (multiselect)
   ========================= */
div[data-baseweb="select"] > div {
    background-color: #FFF7CC !important;
    border-radius: 10px;
}

div[data-baseweb="tag"] {
    background-color: #FFC400 !important;
    color: #081B33 !important;
    font-weight: 700;
    border-radius: 8px;
}

/* Separadores */
hr {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.25);
}

</style>
""", unsafe_allow_html=True)


st.title("Piloto E-Moviliza")

EXCEL_PATH = Path("web/registro_semanal.xlsx")  # Asegúrate que esté en esta ruta

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"No encuentro el archivo: {path}")
        st.stop()

    df = pd.read_excel(path, engine="openpyxl")

    # Validación mínima
    required = {"fecha", "km", "CO2", "Kg", "consumo", "tiempo", "empresa", "dv"}
    missing = required - set(df.columns)
    if missing:
        st.error(f"Faltan columnas en el Excel: {missing}\nColumnas encontradas: {list(df.columns)}")
        st.stop()

    # Tipos
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"])

    for c in ["km", "CO2", "Kg", "consumo", "tiempo"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Semana (lunes a domingo)
    df["week_start"] = df["fecha"] - pd.to_timedelta(df["fecha"].dt.weekday, unit="D")
    df["week_end"] = df["week_start"] + pd.Timedelta(days=6)
    df["semana"] = df["week_start"].dt.strftime("%Y-%m-%d") + " a " + df["week_end"].dt.strftime("%Y-%m-%d")

    return df

df = load_data(EXCEL_PATH)

# -------------------------------
# Filtros horizontales
# -------------------------------
st.markdown("---")
st.subheader("🎛️ Filtros")

semanas = sorted(df["semana"].unique().tolist())

f1, f2, f3 = st.columns(3)

with f1:
    semanas_sel = st.multiselect("Semana(s)", options=semanas, default=semanas)

# Filtrar por semana para poblar empresas válidas
df_w = df[df["semana"].isin(semanas_sel)].copy() if semanas_sel else df.copy()
empresas = sorted(df_w["empresa"].dropna().unique().tolist())

with f2:
    emp_sel = st.multiselect("Empresa(s)", options=empresas, default=empresas)

# Filtrar por empresa para poblar dvs válidos
df_we = df_w[df_w["empresa"].isin(emp_sel)].copy() if emp_sel else df_w.copy()
dvs = sorted(df_we["dv"].dropna().unique().tolist())

with f3:
    dv_sel = st.multiselect("DV(s)", options=dvs, default=dvs)

# Filtro final
df_f = df_we[df_we["dv"].isin(dv_sel)].copy() if dv_sel else df_we.copy()

#st.caption(f"Registros filtrados: **{len(df_f)}**")


# st.caption(f"Registros filtrados: **{len(df_f)}**")

# -------------------------------
# KPIs (para la selección actual)
# -------------------------------
total_km = float(df_f["km"].sum())
total_co2 = float(df_f["CO2"].sum())
total_kg = float(df_f["Kg"].sum())
total_tiempo = float(df_f["tiempo"].sum())
total_kwh = float(df_f["consumo"].sum())

kwh_km = (total_kwh / total_km) if total_km > 0 else 0.0

st.subheader("📌 KPIs (selección actual)")

r1 = st.columns(3)
r2 = st.columns(3)

def kpi_card(col, icon, label, value, sub=""):
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-top">
            <div class="kpi-label">{label}</div>
            <div class="kpi-icon">{icon}</div>
        </div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

kpi_card(r1[0], "🚗", "Km recorridos", f"{total_km:,.2f}", "Total según filtros")
kpi_card(r1[1], "🌱", "CO₂ (kg CO₂-eq)", f"{total_co2:,.2f}", "Total según filtros")
kpi_card(r1[2], "📦", "Kg transportados", f"{total_kg:,.0f}", "Total según filtros")

kpi_card(r2[0], "⏱️", "Tiempo de ruta (h)", f"{total_tiempo:,.2f}", "Total según filtros")
kpi_card(r2[1], "⚡", "Consumo (kWh)", f"{total_kwh:,.2f}", "Total según filtros")
kpi_card(r2[2], "⚡", "kWh/km", f"{kwh_km:,.3f}", "Consumo específico")


st.markdown("---")

# -------------------------------
# Totales por empresa (selección actual)
# -------------------------------
st.subheader("🏢 Totales por empresa (selección actual)")

df_emp = (
    df_f.groupby("empresa", as_index=False)
        .agg({
            "km": "sum",
            "CO2": "sum",
            "Kg": "sum",
            "tiempo": "sum",
            "consumo": "sum"
        })
)

df_emp["kWh/km"] = df_emp.apply(lambda r: (r["consumo"] / r["km"]) if r["km"] > 0 else 0.0, axis=1)

df_emp = df_emp.rename(columns={
    "km": "Km",
    "CO2": "CO₂",
    "Kg": "Kg transportados",
    "tiempo": "Tiempo (h)",
    "consumo": "Consumo (kWh)"
}).sort_values("Km", ascending=False)

st.dataframe(df_emp, use_container_width=True, hide_index=True)

st.markdown("---")

# -------------------------------
# Función para crear pivots semanales por empresa
# -------------------------------
def weekly_pivot(metric_col: str) -> pd.DataFrame:
    df_week = (
        df_f.groupby(["week_start", "empresa"], as_index=False)[metric_col]
            .sum()
            .sort_values("week_start")
    )
    piv = df_week.pivot(index="week_start", columns="empresa", values=metric_col).fillna(0)
    piv.index.name = "Semana"
    return piv

# -------------------------------
# Gráficas: semanas vs métricas (curvas por empresa)
# -------------------------------
st.subheader("📈 Evolución semanal por empresa")

tab1, tab2, tab3, tab4 = st.tabs([
    "Km por semana",
    "Consumo kWh por semana",
    "Tiempo por semana",
    "Kg transportados por semana"
])

with tab1:
    piv = weekly_pivot("km")
    st.line_chart(piv)

with tab2:
    piv = weekly_pivot("consumo")
    st.line_chart(piv)

with tab3:
    piv = weekly_pivot("tiempo")
    st.line_chart(piv)

with tab4:
    piv = weekly_pivot("Kg")
    st.line_chart(piv)
