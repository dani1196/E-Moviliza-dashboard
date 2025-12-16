import streamlit as st
import pandas as pd
from datetime import date
import altair as alt


# -------------------------------
# Config página + estilo (fondo azul marino)
# -------------------------------
st.set_page_config(page_title="Tablero Operacional", layout="wide")

st.markdown("""
<style>
.kpi-grid { display: grid; gap: 16px; }
.kpi-grid.cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.kpi-grid.cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }

@media (max-width: 900px){
  .kpi-grid.cols-3, .kpi-grid.cols-2 { grid-template-columns: 1fr; }
}

.kpi-box{
  background: #F2C94C;   /* amarillo */
  border: none;          /* sin borde */
  box-shadow: none;      /* sin sombra */
  border-radius: 18px;
  padding: 18px;
}

.kpi-box .top{
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom: 10px;
}
.kpi-box .label{
  color:#111827;
  font-weight: 800;
  font-size: 1.0rem;
}
.kpi-box .icon{ font-size: 20px; }
.kpi-box .value{
  color:#111826;
  font-weight: 900;
  font-size: 2.2rem;
  line-height: 1.05;
}
.kpi-box .sub{
  margin-top: 6px;
  color:#1f2937;
  font-weight: 700;
  font-size: 0.95rem;
  opacity: 0.9;
}
</style>
""", unsafe_allow_html=True)



st.title("Piloto E-Moviliza")

# -------------------------------
# Helpers de lectura
# -------------------------------
def _read_excel_any_sheet(excel_file, sheet_try):
    """
    Intenta leer una hoja por nombre o índice.
    sheet_try puede ser: ["Hoja2", "Sheet2", 1] etc.
    """
    last_err = None
    for sh in sheet_try:
        try:
            return pd.read_excel(excel_file, sheet_name=sh)
        except Exception as e:
            last_err = e
    raise last_err


@st.cache_data
def load_daily_data(excel_file) -> pd.DataFrame:
    """
    Carga la hoja principal (primera hoja) con columnas diarias:
    fecha, km, Kg, tiempo, empresa
    """
    df = pd.read_excel(excel_file, sheet_name=0)
    df.columns = [c.strip() for c in df.columns]

    # Asegura fecha como datetime
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # Asegura numéricos
    for col in ["km", "Kg", "tiempo"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["fecha"])
    return df


@st.cache_data
def load_kpis_hoja2_por_marca(excel_file):
    """
    Hoja2 tiene 4 bloques:
    fila header: periodo | consumo | km | CO2 URBANO | <empresa> | <marca>
    filas data:  valores (con coma decimal)

    Retorna:
      {
        "BYD": {"consumo":..., "km":..., "kwh_km":..., "co2":...},
        "FRZ": {"consumo":..., "km":..., "kwh_km":..., "co2":...},
      }
    """
    df2 = pd.read_excel(excel_file, sheet_name="Hoja2", header=None)

    def canon_marca(x):
        s = str(x).strip().upper()
        s = s.replace(".", "")  # por si viene "FRZ."
        if s.startswith("BYD"):
            return "BYD"
        if s.startswith("FRZ") or "FARIZON" in s:
            return "FRZ"
        return None

    def to_float(x):
        # Convierte "201,6" -> 201.6 y maneja NaN
        if pd.isna(x):
            return None
        s = str(x).strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    acc = {
        "BYD": {"consumo": 0.0, "km": 0.0, "co2": 0.0},
        "FRZ": {"consumo": 0.0, "km": 0.0, "co2": 0.0},
    }

    # detecta cada bloque: fila donde col0 == "periodo"
    for i in range(len(df2)):
        v0 = df2.iloc[i, 0]
        if isinstance(v0, str) and v0.strip().lower() == "periodo":
            marca = canon_marca(df2.iloc[i, 5])  # BYD / FRZ (en el header del bloque)
            if marca is None:
                continue

            r = i + 1
            # termina bloque cuando la columna "periodo" (col0) está vacía
            while r < len(df2) and pd.notna(df2.iloc[r, 0]):
                consumo = to_float(df2.iloc[r, 1])
                km      = to_float(df2.iloc[r, 2])
                co2     = to_float(df2.iloc[r, 3])

                if consumo is not None: acc[marca]["consumo"] += consumo
                if km      is not None: acc[marca]["km"]      += km
                if co2     is not None: acc[marca]["co2"]     += co2

                r += 1

    # Calcula kWh/km = consumo_total / km_total
    for m in acc:
        km = acc[m]["km"]
        acc[m]["kwh_km"] = (acc[m]["consumo"] / km) if km > 0 else float("nan")

    return acc



# -------------------------------
# Utilidades
# -------------------------------
def format_hours_to_hm(hours: float) -> str:
    if pd.isna(hours):
        return "—"
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def totals_block(df_in: pd.DataFrame):
    total_km = df_in["km"].sum(skipna=True)
    total_kg = df_in["Kg"].sum(skipna=True)
    total_tiempo_h = df_in["tiempo"].sum(skipna=True)
    return total_km, total_kg, total_tiempo_h


# -------------------------------
# Carga de datos
# -------------------------------
DEFAULT_PATH = "web/registro_semanal_completo.xlsx"

try:
    excel_source = DEFAULT_PATH
    df = load_daily_data(excel_source)
except Exception:
    st.error(
        "No pude abrir 'registro_semanal.xlsx'. "
        "Asegúrate de que esté en la misma carpeta que app.py."
    )
    st.stop()

# Validación de columnas necesarias
required = {"fecha", "km", "Kg", "tiempo", "empresa"}
missing = required - set(df.columns)
if missing:
    st.error(f"Faltan columnas en la hoja principal del Excel: {missing}")
    st.stop()

def kpi_box(label, value, icon="✨", sub=None):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-box">
      <div class="top">
        <div class="label">{label}</div>
        <div class="icon">{icon}</div>
      </div>
      <div class="value">{value}</div>
      {sub_html}
    </div>
    """

# -------------------------------
# KPIs FIJOS (18-ago a 12-nov) — NO dependen del filtro
# -------------------------------
st.subheader("🔒 Totales generales (18-ago a 12-nov)")

start_fixed = pd.Timestamp(date(2025, 8, 18))
end_fixed = pd.Timestamp(date(2025, 11, 12))

df_fixed = df[(df["fecha"] >= start_fixed) & (df["fecha"] <= end_fixed)].copy()
km_fixed, kg_fixed, t_fixed = totals_block(df_fixed)

# KPIs extra desde Hoja2
# KPIs extra desde Hoja2 por marca
kpis_marca = {"BYD": {"kwh_km": float("nan"), "co2": float("nan")},
              "FRZ": {"kwh_km": float("nan"), "co2": float("nan")}}

try:
    kpis_marca = load_kpis_hoja2_por_marca(excel_source)
except Exception:
    pass

# Primera fila (3 KPIs)
# Valores para KPIs por marca
byd_kwhkm = "—" if pd.isna(kpis_marca["BYD"]["kwh_km"]) else f'{kpis_marca["BYD"]["kwh_km"]:.3f}'
frz_kwhkm = "—" if pd.isna(kpis_marca["FRZ"]["kwh_km"]) else f'{kpis_marca["FRZ"]["kwh_km"]:.3f}'

byd_co2 = "—" if pd.isna(kpis_marca["BYD"]["co2"]) else f'{kpis_marca["BYD"]["co2"]:,.2f}'
frz_co2 = "—" if pd.isna(kpis_marca["FRZ"]["co2"]) else f'{kpis_marca["FRZ"]["co2"]:,.2f}'

# Fila 1 (3 KPIs)
st.markdown(
    f"""
    <div class="kpi-grid cols-3">
      {kpi_box("Total km recorridos", f"{km_fixed:,.1f}", "🚚")}
      {kpi_box("Total kg transportados", f"{kg_fixed:,.1f}", "📦")}
      {kpi_box("Total tiempo en movimiento", f"{t_fixed:,.2f} h", "⏱️", sub=format_hours_to_hm(t_fixed))}
    </div>
    """,
    unsafe_allow_html=True
)

# Fila 2 (2 KPIs)
st.markdown(
    f"""
    <div class="kpi-grid cols-2" style="margin-top: 12px;">
      {kpi_box("Consumo energético por km BYD (kWh/km)", byd_kwhkm, "🔋")}
      {kpi_box("Consumo energético por km FRZ (kWh/km)", frz_kwhkm, "🔋")}
    </div>
    """,
    unsafe_allow_html=True
)

# Fila 3 (2 KPIs)
st.markdown(
    f"""
    <div class="kpi-grid cols-2" style="margin-top: 12px;">
      {kpi_box("kg CO₂-eq BYD", byd_co2, "🌱")}
      {kpi_box("kg CO₂-eq FRZ (kg)", frz_co2, "🌱")}
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

# -------------------------------
# FILTROS (para tabla + gráficas)
# -------------------------------
st.subheader("🎛️ Filtros para tablas y gráficas")

min_date = df["fecha"].min().date()
max_date = df["fecha"].max().date()

empresas = sorted(df["empresa"].dropna().unique().tolist())
emp_options = ["Todas"] + empresas

colf1, colf2 = st.columns([2, 1])

with colf1:
    date_range = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

with colf2:
    emp_sel = st.selectbox("Empresa", emp_options, index=0)

if isinstance(date_range, tuple) and len(date_range) == 2:
    d1, d2 = date_range
else:
    d1, d2 = min_date, max_date

d1_ts = pd.Timestamp(d1)
d2_ts = pd.Timestamp(d2)

df_f = df[(df["fecha"] >= d1_ts) & (df["fecha"] <= d2_ts)].copy()
if emp_sel != "Todas":
    df_f = df_f[df_f["empresa"] == emp_sel].copy()

# -------------------------------
# TABLA DE TOTALES (según filtro)
# -------------------------------
st.subheader("📌 Totales según filtro")

km_f, kg_f, t_f = totals_block(df_f)

resumen = pd.DataFrame(
    {
        "Fecha inicio": [d1],
        "Fecha fin": [d2],
        "Empresa": [emp_sel],
        "Total km": [km_f],
        "Total kg": [kg_f],
        "Total tiempo (h)": [t_f],
        "Total tiempo (HH:MM)": [format_hours_to_hm(t_f)],
        "N registros": [len(df_f)],
    }
)

st.dataframe(resumen, use_container_width=True, hide_index=True)



st.markdown("---")

# -------------------------------
# GRÁFICAS (Altair: eje X en fechas, sin 12 PM)
# -------------------------------
st.subheader("📈 Gráficas")

# Asegura fecha sin hora (solo día)
df_f = df_f.copy()
df_f["fecha"] = pd.to_datetime(df_f["fecha"]).dt.normalize()  # 00:00:00 siempre

tab_km, tab_kg, tab_t = st.tabs(["🛣️ Km", "📦 Kg", "⏱️ Tiempo"])

def make_line_chart(df_plot: pd.DataFrame, y_col: str, y_title: str):
    return (
        alt.Chart(df_plot)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "fecha:T",
                title="Fecha",
                axis=alt.Axis(
                    format="%a %d",   # lun 18 (depende de locale del sistema)
                    labelAngle=0,
                    tickCount="day"
                ),
            ),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            color=alt.Color("empresa:N", title="Empresa"),
            tooltip=[
                alt.Tooltip("fecha:T", title="Fecha", format="%A %d"),
                alt.Tooltip("empresa:N", title="Empresa"),
                alt.Tooltip(f"{y_col}:Q", title=y_title, format=",.2f"),
            ],
        )
        .properties(height=420)
        .interactive()
    )

def build_data(y_col: str):
    if emp_sel == "Todas":
        # 4 curvas: agrupa por fecha y empresa
        out = (
            df_f.groupby(["fecha", "empresa"], as_index=False)[y_col]
            .sum()
        )
    else:
        # 1 curva: agrupa solo por fecha y asigna empresa seleccionada
        out = (
            df_f.groupby("fecha", as_index=False)[y_col]
            .sum()
            .assign(empresa=emp_sel)
        )
    return out

with tab_km:
    st.write("**Fecha vs km recorridos**")
    data_km = build_data("km")
    st.altair_chart(make_line_chart(data_km, "km", "Km recorridos"), use_container_width=True)

with tab_kg:
    st.write("**Fecha vs kg transportados**")
    data_kg = build_data("Kg")
    st.altair_chart(make_line_chart(data_kg, "Kg", "Kg transportados"), use_container_width=True)

with tab_t:
    st.write("**Fecha vs tiempo en movimiento (h)**")
    data_t = build_data("tiempo")
    st.altair_chart(make_line_chart(data_t, "tiempo", "Tiempo en movimiento (h)"), use_container_width=True)
