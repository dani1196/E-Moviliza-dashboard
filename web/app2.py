import streamlit as st
import pandas as pd
from datetime import date
import altair as alt


# -------------------------------
# Config página + estilo (fondo azul marino)
# -------------------------------
st.set_page_config(page_title="Tablero Operacional", layout="wide")

st.markdown(
    """
<style>
.kpi-grid { display: grid; gap: 16px; }
.kpi-grid.cols-1 { grid-template-columns: 1fr; }
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
            
<style>
/* KPI especial para CO2 */
/* KPI especial para CO2 */
/* KPI especial para CO2 */
.kpi-co2 {
  background: #22C55E;      /* verde */
  text-align: center;
}

.kpi-co2 .label {
  color: #000000;           /* negro */
  font-size: 1.1rem;
  font-weight: 800;
}

.kpi-co2 .value {
  color: #000000;           /* negro */
  font-size: 3.0rem;
  font-weight: 900;
}

.kpi-co2 .icon {
  color: #000000;           /* negro */
  font-size: 22px;
}

</style>
""",
    unsafe_allow_html=True,
)


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
def load_kpis_hoja2_totales(excel_file):
    """
    Hoja2:
    header: periodo | consumo | km | CO2 URBANO | <empresa> | <marca>
    filas:  valores (coma decimal)

    Retorna:
      consumo_total (kWh)
      km_total (km)
      co2_total (kg)
    """
    df2 = pd.read_excel(excel_file, sheet_name="Hoja2", header=None)

    def to_float(x):
        if pd.isna(x):
            return None
        s = str(x).strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    consumo_total = 0.0
    km_total = 0.0
    co2_total = 0.0

    for i in range(len(df2)):
        v0 = df2.iloc[i, 0]
        if isinstance(v0, str) and v0.strip().lower() == "periodo":
            r = i + 1
            while r < len(df2) and pd.notna(df2.iloc[r, 0]):
                consumo = to_float(df2.iloc[r, 1])  # consumo
                km = to_float(df2.iloc[r, 2])  # km
                co2 = to_float(df2.iloc[r, 3])  # CO2 urbano

                if consumo is not None:
                    consumo_total += consumo
                if km is not None:
                    km_total += km
                if co2 is not None:
                    co2_total += co2

                r += 1

    return consumo_total, km_total, co2_total


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

# -------------------------------
# KPIs FIJOS (18-ago a 12-nov) — NO dependen del filtro
# -------------------------------


def kpi_box(label, value, icon="✨", sub=None, extra_class=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-box {extra_class}">
      <div class="top">
        <div class="label">{label}</div>
        <div class="icon">{icon}</div>
      </div>
      <div class="value">{value}</div>
      {sub_html}
    </div>
    """


st.subheader("🔒 Totales generales (18-ago a 12-nov)")

N_EMPRESAS = 4
N_HOMBRES = 6
N_MUJERES = 1
COSTO_KWH_USD = 0.1715
TOTAL_CONDUCTORES = N_HOMBRES + N_MUJERES

start_fixed = pd.Timestamp(date(2025, 8, 18))
end_fixed = pd.Timestamp(date(2025, 11, 12))

df_fixed = df[(df["fecha"] >= start_fixed) & (df["fecha"] <= end_fixed)].copy()
km_fixed, kg_fixed, t_fixed = totals_block(df_fixed)

# KPIs extra desde Hoja2
consumo_total = float("nan")
km_total_hoja2 = float("nan")
co2_total = float("nan")

try:
    consumo_total, km_total_hoja2, co2_total = load_kpis_hoja2_totales(excel_source)
except Exception:
    pass

consumo_kwh_km = (
    consumo_total / km_total_hoja2
    if pd.notna(consumo_total) and pd.notna(km_total_hoja2) and km_total_hoja2 > 0
    else float("nan")
)

costo_total_usd = (
    consumo_total * COSTO_KWH_USD if pd.notna(consumo_total) else float("nan")
)

# Costo por km
costo_usd_km = (
    consumo_kwh_km * COSTO_KWH_USD if pd.notna(consumo_kwh_km) else float("nan")
)

costo_ctvs_km = costo_usd_km * 100 if pd.notna(costo_usd_km) else float("nan")

# Enteros
km_txt = "—" if pd.isna(km_fixed) else f"{int(round(km_fixed)):,}"
kg_txt = "—" if pd.isna(kg_fixed) else f"{int(round(kg_fixed)):,}"
co2_txt = "—" if pd.isna(co2_total) else f"{int(round(co2_total)):,}"

# Tiempo solo h:mm
time_hm_txt = format_hours_to_hm(t_fixed)

# Razones / costos
consumo_kwh_km_txt = (
    "—"
    if pd.isna(consumo_kwh_km)
    else f"{consumo_kwh_km:.3f} ({costo_ctvs_km:.2f} ctvs./km)"
)

costo_usd_txt = "—" if pd.isna(costo_total_usd) else f"USD {costo_total_usd:,.2f}"

# Fila 1
st.markdown(
    f"""
    <div class="kpi-grid cols-1" style="margin-top: 12px;">
      {kpi_box("Emisiones de CO₂ evitadas (kg)", co2_txt, "♻️", extra_class="kpi-co2")}
    </div>
    """,
    unsafe_allow_html=True,
)


# Fila 2 (3 KPIs)

st.markdown(
    f"""
    <div class="kpi-grid cols-3" style="margin-top: 12px;">
      {kpi_box("Distancia total recorrida (km)", km_txt, "🚚")}
      {kpi_box("Carga total transportada (kg)", kg_txt, "📦")}
      {kpi_box("Tiempo total en movimiento (hh:mm)", time_hm_txt, "⏱️")}
    </div>
    """,
    unsafe_allow_html=True,
)

# Fila 3
st.markdown(
    f"""
    <div class="kpi-grid cols-3" style="margin-top: 12px;">
      {
        kpi_box(
            "Consumo energético (kWh/km)",
            consumo_kwh_km_txt,
            "🔋",
            sub=f"Tarifario CNEL 2025: 17.15 ctvs/kWh",
        )
    }
    {kpi_box("Empresas participantes", f"{N_EMPRESAS}", "🏢")}
    {
        kpi_box(
            "Consumo combustible (gL/km)",
            "0.027 (0.07 ctvs/km)",
            "⛽",
            sub="Fuelly (Hyundai H1 2009)",
        )
    }
      {
        kpi_box(
            "Conductores Hombres/Conductoras Mujeres ",
            f"{N_HOMBRES} / {N_MUJERES}",
            "👥",
        )
    }
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown("---")

# -------------------------------
# FILTROS (para tabla + gráficas)
# -------------------------------
st.subheader("🎛️ Filtros para tablas y gráficas")

min_date = df["fecha"].min().date()
max_date = df["fecha"].max().date()

empresas = sorted(df["empresa"].dropna().unique().tolist())

colf1, colf2 = st.columns([2, 1])

with colf1:
    date_range = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

with colf2:
    emp_sel_list = st.multiselect(
        "Empresa(s)",
        options=empresas,
        default=empresas,  # por defecto: todas seleccionadas
    )

# Garantiza al menos una empresa seleccionada
if not emp_sel_list:
    emp_sel_list = empresas[:]  # vuelve a seleccionar todas
    st.warning("Selecciona al menos una empresa. Se seleccionaron todas por defecto.")

if isinstance(date_range, tuple) and len(date_range) == 2:
    d1, d2 = date_range
else:
    d1, d2 = min_date, max_date

d1_ts = pd.Timestamp(d1)
d2_ts = pd.Timestamp(d2)

df_f = df[(df["fecha"] >= d1_ts) & (df["fecha"] <= d2_ts)].copy()
df_f = df_f[df_f["empresa"].isin(emp_sel_list)].copy()


# -------------------------------
# TABLA DE TOTALES (según filtro)
# -------------------------------
st.subheader("📌 Totales según filtro")

# Agrupa por empresa
resumen = (
    df_f.groupby("empresa")
    .agg(
        **{
            "Km recorridos": ("km", "sum"),
            "Kg transportados": ("Kg", "sum"),
            "Tiempo en movimiento (h)": ("tiempo", "sum"),
        }
    )
    .reset_index()
)

# Agrega fechas del filtro
resumen.insert(0, "Fecha inicio", d1)
resumen.insert(1, "Fecha fin", d2)

# Columna HH:MM
resumen["Tiempo en movimiento (HH:MM)"] = resumen["Tiempo en movimiento (h)"].apply(
    format_hours_to_hm
)

# Reordena columnas (opcional, más limpio)
resumen = resumen[
    [
        "Fecha inicio",
        "Fecha fin",
        "empresa",
        "Km recorridos",
        "Kg transportados",
        "Tiempo en movimiento (h)",
        "Tiempo en movimiento (HH:MM)",
    ]
]

# Renombra columna empresa para presentación
resumen = resumen.rename(columns={"empresa": "Empresa"})

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
                    format="%a %d",  # lun 18 (depende de locale del sistema)
                    labelAngle=0,
                    tickCount="day",
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
    out = df_f.groupby(["fecha", "empresa"], as_index=False)[y_col].sum()
    return out


with tab_km:
    st.write("**Fecha vs km recorridos**")
    data_km = build_data("km")
    st.altair_chart(
        make_line_chart(data_km, "km", "Km recorridos"), use_container_width=True
    )

with tab_kg:
    st.write("**Fecha vs kg transportados**")
    data_kg = build_data("Kg")
    st.altair_chart(
        make_line_chart(data_kg, "Kg", "Kg transportados"), use_container_width=True
    )

with tab_t:
    st.write("**Fecha vs tiempo en movimiento (h)**")
    data_t = build_data("tiempo")
    st.altair_chart(
        make_line_chart(data_t, "tiempo", "Tiempo en movimiento (h)"),
        use_container_width=True,
    )
