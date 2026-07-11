"""
Limpieza y consolidación de datos: Pobreza y costo de vida por región del Perú
Fuentes:
  - descarga.xls (SIRTOD-INEI): pobreza e ingreso laboral por DEPARTAMENTO, 2004-2025
  - 02_Lineas_..., 01_Gastos_..., 01_Ingresos_..., 03_FGT_...: costo de vida por DOMINIO geográfico, 2015-2024
"""
import pandas as pd
import openpyxl
import re
import json

# ---------------------------------------------------------------------------
# 1. POBREZA E INGRESO LABORAL POR DEPARTAMENTO (SIRTOD)
# ---------------------------------------------------------------------------
raw = pd.read_html("raw_data_original/descarga.xls")[0]
raw.columns = [c[1] if isinstance(c, tuple) else c for c in raw.columns]
raw = raw.rename(columns={raw.columns[0]: "departamento", raw.columns[1]: "indicador"})
raw = raw.drop(columns=["Unnamed: 2_level_1"], errors="ignore")
raw = raw.dropna(subset=["departamento"])
raw = raw[raw["departamento"] != "DEPARTAMENTO"]

year_cols = [c for c in raw.columns if str(c).isdigit()]

def parse_range_or_number(val):
    """Convierte '24,4 - 28,0' -> (24.4, 28.0, 26.2). Convierte '1 240,4' -> 1240.4 (numero simple)."""
    if val is None or (isinstance(val, float) and pd.isna(val)) or val == "-":
        return (None, None, None)
    s = str(val).strip()
    if "-" in s and "," in s:
        parts = s.split("-")
        if len(parts) == 2:
            try:
                lo = float(parts[0].strip().replace(" ", "").replace(",", "."))
                hi = float(parts[1].strip().replace(" ", "").replace(",", "."))
                return (lo, hi, round((lo + hi) / 2, 2))
            except ValueError:
                pass
    # numero simple (ingreso): formato normal "1 240,4" -> 1240.4
    if "," in s or " " in s:
        s2 = s.replace(" ", "").replace(",", ".")
        try:
            num = float(s2)
            return (num, num, num)
        except ValueError:
            return (None, None, None)
    # SIRTOD exporta algunos valores de ingreso sin coma decimal, ej. "9391" en vez
    # de "939,1" (perdio el separador). Se detecta porque son enteros de 4 digitos
    # sin coma mientras el resto de la serie de la misma columna SI trae coma;
    # dividir entre 10 restaura la magnitud correcta y consistente con la serie.
    if s.isdigit() and len(s) == 4:
        return (float(s) / 10, float(s) / 10, float(s) / 10)
    try:
        num = float(s)
        return (num, num, num)
    except ValueError:
        return (None, None, None)

records = []
for _, row in raw.iterrows():
    dept = row["departamento"]
    indicador = row["indicador"]
    for yr in year_cols:
        lo, hi, mid = parse_range_or_number(row[yr])
        if mid is None:
            continue
        records.append({
            "departamento": dept,
            "anio": int(yr),
            "indicador": indicador,
            "valor_min": lo,
            "valor_max": hi,
            "valor": mid,
        })

df_long = pd.DataFrame(records)

# nombres de indicador mas cortos
indicador_map = {
    "Incidencia de pobreza por grupos de departamentos según intervalos de confianza": "pobreza_total_pct",
    "Incidencia de pobreza extrema por grupos de departamentos según intervalos de confianza": "pobreza_extrema_pct",
    "Ingreso promedio mensual proveniente del trabajo": "ingreso_laboral_soles",
}
df_long["indicador"] = df_long["indicador"].map(indicador_map)

df_departamento = df_long.pivot_table(
    index=["departamento", "anio"], columns="indicador", values="valor"
).reset_index()

# tambien guardamos min/max de pobreza para mostrar el intervalo de confianza en la app
df_conf = df_long[df_long["indicador"].isin(["pobreza_total_pct", "pobreza_extrema_pct"])].pivot_table(
    index=["departamento", "anio"], columns="indicador", values=["valor_min", "valor_max"]
)
df_conf.columns = [f"{a}_{b}" for a, b in df_conf.columns]
df_conf = df_conf.reset_index()

df_departamento = df_departamento.merge(df_conf, on=["departamento", "anio"], how="left")
df_departamento["departamento"] = df_departamento["departamento"].str.strip()

# ---------------------------------------------------------------------------
# 2. MAPEO DEPARTAMENTO -> REGION NATURAL (Costa / Sierra / Selva)
# ---------------------------------------------------------------------------
region_natural = {
    "AMAZONAS": "Selva", "ÁNCASH": "Costa", "ANCASH": "Costa", "APURÍMAC": "Sierra", "APURIMAC": "Sierra",
    "AREQUIPA": "Costa", "AYACUCHO": "Sierra", "CAJAMARCA": "Sierra", "CALLAO": "Costa",
    "CUSCO": "Sierra", "HUANCAVELICA": "Sierra", "HUÁNUCO": "Sierra", "HUANUCO": "Sierra",
    "ICA": "Costa", "JUNÍN": "Sierra", "JUNIN": "Sierra", "LA LIBERTAD": "Costa",
    "LAMBAYEQUE": "Costa", "LIMA METROPOLITANA 1/": "Lima Metropolitana", "LIMA 2/": "Costa",
    "LORETO": "Selva", "MADRE DE DIOS": "Selva", "MOQUEGUA": "Costa", "PASCO": "Sierra",
    "PIURA": "Costa", "PUNO": "Sierra", "SAN MARTÍN": "Selva", "SAN MARTIN": "Selva",
    "TACNA": "Costa", "TUMBES": "Costa", "UCAYALI": "Selva", "LIMA": "Costa",
}
df_departamento["region_natural"] = df_departamento["departamento"].str.upper().map(region_natural)

missing = df_departamento[df_departamento["region_natural"].isna()]["departamento"].unique()
print("Departamentos sin mapear (revisar):", list(missing))

# ---------------------------------------------------------------------------
# 3. LÍNEA DE POBREZA POR REGIÓN NATURAL (costo de vida oficial INEI)
# ---------------------------------------------------------------------------
def leer_cuadro_region_natural(path, sheet, nombre_valor):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))

    def es_anio(v):
        try:
            return 2015 <= int(v) <= 2024
        except (TypeError, ValueError):
            return False

    header_row = next(r for r in rows if any(es_anio(c) for c in r))
    year_idx = {int(c): i for i, c in enumerate(header_row) if es_anio(c)}

    out = []
    etiquetas_exactas = {"Costa", "Sierra", "Selva"}
    ya_visto = set()  # cada región solo debe tomarse de su PRIMERA aparición
    # (las tablas repiten las etiquetas más abajo como cabecera de un desglose por deciles)
    for row in rows:
        label = row[0]
        if not isinstance(label, str):
            continue
        label_s = label.strip()
        if label_s in etiquetas_exactas:
            region = label_s
        elif label_s.startswith("Lima Metropolitana"):
            region = "Lima Metropolitana"
        else:
            continue
        if region in ya_visto:
            continue
        ya_visto.add(region)
        for yr, idx in year_idx.items():
            val = row[idx]
            if val is not None:
                out.append({"region_natural": region, "anio": yr, nombre_valor: val})
    return pd.DataFrame(out)

df_linea_total = leer_cuadro_region_natural(
    "raw_data_original/02_Lineas_Total_y_Extrema_2015-2024_informe.xlsx", "II.2", "linea_pobreza_total_soles"
)
df_linea_extrema = leer_cuadro_region_natural(
    "raw_data_original/02_Lineas_Total_y_Extrema_2015-2024_informe.xlsx", "II.1", "linea_pobreza_extrema_soles"
)
df_gasto = leer_cuadro_region_natural(
    "raw_data_original/01_Gastos_reales_nominales_2015_2024_informe.xlsx", "I.1", "gasto_real_soles"
)
df_ingreso = leer_cuadro_region_natural(
    "raw_data_original/01_Ingresos_Reales_nominales__2015-2024_informe.xlsx", "I.15", "ingreso_real_soles"
)

df_dominio = df_linea_total.merge(df_linea_extrema, on=["region_natural", "anio"], how="outer")
df_dominio = df_dominio.merge(df_gasto, on=["region_natural", "anio"], how="outer")
df_dominio = df_dominio.merge(df_ingreso, on=["region_natural", "anio"], how="outer")

# ---------------------------------------------------------------------------
# 4. TABLA MAESTRA: departamento + su región natural + costo de vida de esa región
# ---------------------------------------------------------------------------
df_maestro = df_departamento.merge(df_dominio, on=["region_natural", "anio"], how="left")

# Indicador propio: brecha de poder adquisitivo
# (ingreso laboral departamental) vs (línea de pobreza total de su región natural)
df_maestro["brecha_poder_adquisitivo"] = (
    df_maestro["ingreso_laboral_soles"] - df_maestro["linea_pobreza_total_soles"]
)
df_maestro["brecha_poder_adquisitivo_pct"] = (
    df_maestro["brecha_poder_adquisitivo"] / df_maestro["linea_pobreza_total_soles"] * 100
)

# ---------------------------------------------------------------------------
# 5. GUARDAR
# ---------------------------------------------------------------------------
df_departamento.to_csv("data/pobreza_departamento.csv", index=False)
df_dominio.to_csv("data/costo_vida_region_natural.csv", index=False)
df_maestro.to_csv("data/tabla_maestra.csv", index=False)

print("\n--- pobreza_departamento.csv ---")
print(df_departamento.shape)
print(df_departamento.head(3).to_string())

print("\n--- costo_vida_region_natural.csv ---")
print(df_dominio.shape)
print(df_dominio.head(3).to_string())

print("\n--- tabla_maestra.csv ---")
print(df_maestro.shape)
print(df_maestro[df_maestro["anio"] == 2024][
    ["departamento", "anio", "pobreza_total_pct", "ingreso_laboral_soles",
     "linea_pobreza_total_soles", "brecha_poder_adquisitivo_pct"]
].sort_values("brecha_poder_adquisitivo_pct").to_string())
