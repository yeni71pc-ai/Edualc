# Pobreza y costo de vida real por región del Perú

App interactiva que cruza la pobreza monetaria y el ingreso laboral por
departamento con la línea de pobreza (costo de vida oficial del INEI) de
su región natural, para construir un indicador propio: la **brecha de
poder adquisitivo**.

## Fuentes de datos
- **SIRTOD-INEI**: incidencia de pobreza total/extrema e ingreso laboral
  promedio, por departamento, 2004-2025.
  https://systems.inei.gob.pe/SIRTOD/
- **INEI, Informe Técnico "Perú: Evolución de la Pobreza Monetaria,
  2015-2024"**: línea de pobreza, gasto real e ingreso real, por región
  natural (Costa/Sierra/Selva/Lima Metropolitana).
  https://www.gob.pe/institucion/inei/informes-publicaciones/6763186
- **GeoJSON de departamentos**: juaneladio/peru-geojson (GitHub).

## Indicador propio: brecha de poder adquisitivo
`ingreso_laboral_departamental - línea_de_pobreza_de_su_región_natural`

## Limitaciones (léelas antes de sacar conclusiones)
- La línea de pobreza y el gasto/ingreso real del INEI **no existen a
  nivel de departamento**, solo por región natural (Costa/Sierra/Selva) y
  Lima Metropolitana. Cada departamento hereda el valor de su región
  natural — es una simplificación deliberada, no un dato oficial exacto
  por departamento.
- "Lima Metropolitana" se usa como representante del departamento "Lima"
  en el mapa (concentra ~80% de su población). Los datos separados de
  "Lima provincias" (Lima 2/) existen en la tabla pero no se pintan en
  el mapa por no tener polígono propio en el GeoJSON.
- Los indicadores de pobreza vienen como **rangos de confianza** (INEI
  agrupa departamentos estadísticamente indistinguibles); se usa el
  punto medio del rango para graficar.
- Callao no reporta ingreso laboral por separado en SIRTOD (se agrupa
  con Lima en algunos años).

## Cómo correrla localmente
```
pip install -r requirements.txt
streamlit run app.py
```

## Estructura
```
app.py                     # la app
data/tabla_maestra.csv     # dataset consolidado (departamento x año)
data/mapa_departamento.csv # igual, pero listo para el choropleth
data/peru_departamentos.geojson
01_limpieza.py             # reproduce tabla_maestra.csv desde los Excel crudos
02_preparar_mapa.py        # reproduce mapa_departamento.csv
```
