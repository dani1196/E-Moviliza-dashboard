import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="E-Moviliza | Tablero semanal", layout="wide")
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
# Filtros
# -------------------------------
st.sidebar.header("Filtros")

semanas = sorted(df["semana"].unique().tolist())
semanas_sel = st.sidebar.multiselect("Semana(s)", options=semanas, default=semanas)

df_w = df[df["semana"].isin(semanas_sel)].copy() if semanas_sel else df.copy()

empresas = sorted(df_w["empresa"].dropna().unique().tolist())
emp_sel = st.sidebar.multiselect("Empresa(s)", options=empresas, default=empresas)

df_we = df_w[df_w["empresa"].isin(emp_sel)].copy() if emp_sel else df_w.copy()

dvs = sorted(df_we["dv"].dropna().unique().tolist())
dv_sel = st.sidebar.multiselect("DV(s)", options=dvs, default=dvs)

df_f = df_we[df_we["dv"].isin(dv_sel)].copy() if dv_sel else df_we.copy()

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

# -------- Fila 1 --------
r1c1, r1c2, r1c3 = st.columns(3)

r1c1.metric("🚗 Km recorridos", f"{total_km:,.2f}")
r1c2.metric("🌱 Kg CO₂ - eq", f"{total_co2:,.2f}")
r1c3.metric("📦 Kg transportados", f"{total_kg:,.0f}")

# -------- Fila 2 --------
r2c1, r2c2, r2c3 = st.columns(3)

r2c1.metric("⏱ Tiempo en movimiento (h)", f"{total_tiempo:,.2f}")
r2c2.metric("⚡ Consumo de batería (kWh)", f"{total_kwh:,.2f}")
r2c3.metric("⚡ kWh/km", f"{kwh_km:,.3f}")


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
