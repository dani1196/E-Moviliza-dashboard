import pandas as pd

# --- Ajusta rutas si hace falta ---
infile = "web/registro_semanal.xlsx"
outfile = "web/registro_semanal_completo.xlsx"

# --- Lee hoja principal ---
df = pd.read_excel(infile, sheet_name=0)

# Normaliza columnas (ajusta nombres si en tu archivo están distintos)
df.columns = [c.strip() for c in df.columns]
df["fecha"] = pd.to_datetime(df["fecha"])

# Rango de fechas fijo
start = pd.Timestamp("2025-08-18")
end   = pd.Timestamp("2025-11-12")
full_dates = pd.date_range(start, end, freq="D")

# Lista de empresas
empresas = sorted(df["empresa"].dropna().unique())

# “Plantilla” con todas las combinaciones fecha-empresa
grid = pd.MultiIndex.from_product([full_dates, empresas], names=["fecha", "empresa"]).to_frame(index=False)

# Si tienes varias filas por día/empresa, primero agrupa (recomendado)
df_agg = (
    df.groupby(["fecha", "empresa"], as_index=False)[["km", "Kg", "tiempo"]]
      .sum()
)

# Une el grid con los datos
df_full = grid.merge(df_agg, on=["fecha", "empresa"], how="left")

# Rellena faltantes con 0
for col in ["km", "Kg", "tiempo"]:
    df_full[col] = df_full[col].fillna(0)

# (Opcional) Asegurar tipos
df_full["km"] = df_full["km"].astype(float)
df_full["Kg"] = df_full["Kg"].astype(float)
df_full["tiempo"] = df_full["tiempo"].astype(float)

# --- Escribe a un Excel nuevo, preservando Hoja2 y otras hojas ---
with pd.ExcelWriter(outfile, engine="openpyxl") as writer:
    # Hoja 1 (principal) reemplazada por la versión completa
    df_full.to_excel(writer, sheet_name="Hoja1", index=False)

    # Copia las demás hojas tal cual (incluida Hoja2)
    xls = pd.ExcelFile(infile)
    for sh in xls.sheet_names[1:]:
        pd.read_excel(infile, sheet_name=sh).to_excel(writer, sheet_name=sh, index=False)

print("Listo:", outfile)
