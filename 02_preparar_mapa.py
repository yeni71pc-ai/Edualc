"""Prepara data/mapa_departamento.csv: una fila por departamento del GeoJSON (25),
con los indicadores del año más reciente disponible, lista para el choropleth."""
import pandas as pd
import unicodedata

def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

df = pd.read_csv("data/tabla_maestra.csv")
df["dep_geojson"] = df["departamento"].apply(lambda s: sin_tildes(s).upper().strip())

# casos especiales: el GeoJSON solo tiene UNA región "LIMA" (departamento completo).
# SIRTOD trae "LIMA METROPOLITANA 1/", "LIMA 2/" (=Lima provincias) y "LIMA".
# Usamos Lima Metropolitana como representante de "LIMA" en el mapa (concentra
# ~80% de la población del departamento) — se documenta como simplificación.
df.loc[df["departamento"] == "LIMA METROPOLITANA 1/", "dep_geojson"] = "LIMA"
df.loc[df["departamento"] == "LIMA 2/", "dep_geojson"] = "__DESCARTAR__"  # no se usa en el mapa
df.loc[df["departamento"] == "LIMA", "dep_geojson"] = "__DESCARTAR__"      # idem, evita duplicado

df_mapa = df[df["dep_geojson"] != "__DESCARTAR__"].copy()
df_mapa.to_csv("data/mapa_departamento.csv", index=False)
print(df_mapa["dep_geojson"].nunique(), "departamentos únicos para el mapa")
print(sorted(df_mapa["dep_geojson"].unique()))
