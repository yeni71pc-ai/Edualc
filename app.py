import json
import unicodedata

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Pobreza y costo de vida real en el Perú",
    page_icon="🗺️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# DISEÑO — "cuaderno de campo estadístico andino"
# ---------------------------------------------------------------------------
COLOR_BG = "#FAF8F3"
COLOR_SURFACE = "#FFFFFF"
COLOR_INK = "#2B2320"
COLOR_INK_SOFT = "#6B5F55"
COLOR_COCHINILLA = "#A23B2E"   # acento principal / negativo
COLOR_VERDE_ALTURA = "#1F5C4F"  # positivo
COLOR_ACHIOTE = "#C97A2B"      # terciario
COLOR_LINEA = "#E4DACB"

ESCALA_ROJO_VERDE = [
    [0.0, COLOR_COCHINILLA], [0.5, "#F4E9C9"], [1.0, COLOR_VERDE_ALTURA]
]
ESCALA_SOLO_ROJO = [
    [0.0, "#F4E9C9"], [1.0, COLOR_COCHINILLA]
]

st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] {{
    font-family: 'IBM Plex Sans', sans-serif;
    color: {COLOR_INK};
}}
.stApp {{
    background-color: {COLOR_BG};
}}
[data-testid="stSidebar"] {{
    background-color: {COLOR_SURFACE};
    border-right: 1px solid {COLOR_LINEA};
}}
h1, h2, h3 {{
    font-family: 'Fraunces', serif !important;
    font-weight: 600 !important;
    color: {COLOR_INK} !important;
    letter-spacing: -0.01em;
}}
.faja {{
    height: 8px;
    width: 100%;
    margin: -1rem 0 1.75rem 0;
    background: repeating-linear-gradient(
        90deg,
        {COLOR_COCHINILLA} 0px, {COLOR_COCHINILLA} 28px,
        {COLOR_ACHIOTE} 28px, {COLOR_ACHIOTE} 48px,
        {COLOR_VERDE_ALTURA} 48px, {COLOR_VERDE_ALTURA} 68px,
        {COLOR_INK} 68px, {COLOR_INK} 72px
    );
    border-radius: 2px;
}}
.kpi-card {{
    background: {COLOR_SURFACE};
    border: 1px solid {COLOR_LINEA};
    border-left: 3px solid {COLOR_COCHINILLA};
    border-radius: 6px;
    padding: 0.9rem 1.1rem;
    height: 100%;
    box-shadow: 0 1px 3px rgba(43, 35, 32, 0.06);
}}
.kpi-card.positivo {{ border-left-color: {COLOR_VERDE_ALTURA}; }}
.kpi-label {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: {COLOR_INK_SOFT};
    margin-bottom: 0.3rem;
}}
.kpi-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.5rem;
    font-weight: 600;
    color: {COLOR_INK};
    line-height: 1.15;
}}
.kpi-sub {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    color: {COLOR_INK_SOFT};
    margin-top: 0.15rem;
}}
[data-testid="stMetricValue"], .stDataFrame, .stDataFrame * {{
    font-family: 'IBM Plex Mono', monospace !important;
}}
.stButton>button, .stDownloadButton>button {{
    background-color: {COLOR_COCHINILLA};
    color: white;
    border: none;
}}
hr {{ border-color: {COLOR_LINEA} !important; }}
</style>
""", unsafe_allow_html=True)


def kpi_card(label, value, sub="", positivo=False):
    clase = "kpi-card positivo" if positivo else "kpi-card"
    st.markdown(
        f"""<div class="{clase}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
                <div class="kpi-sub">{sub}</div>
            </div>""",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    maestra = pd.read_csv("data/tabla_maestra.csv")
    mapa = pd.read_csv("data/mapa_departamento.csv")
    with open("data/peru_departamentos.geojson", encoding="utf-8") as f:
        geojson = json.load(f)
    return maestra, mapa, geojson

df, df_mapa, geojson = cargar_datos()

METRICAS = {
    "Brecha de poder adquisitivo (S/)": "brecha_poder_adquisitivo",
    "Brecha de poder adquisitivo (%)": "brecha_poder_adquisitivo_pct",
    "Pobreza total (%)": "pobreza_total_pct",
    "Pobreza extrema (%)": "pobreza_extrema_pct",
    "Ingreso laboral promedio (S/)": "ingreso_laboral_soles",
    "Línea de pobreza de su región natural (S/)": "linea_pobreza_total_soles",
}

ESCALAS_INVERTIDAS = {"pobreza_total_pct", "pobreza_extrema_pct"}  # rojo = peor = más alto

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
st.sidebar.title("🗺️ Pobreza y costo de vida")
st.sidebar.caption("Perú, por departamento — INEI / SIRTOD, 2015-2024")

anios_disponibles = sorted(df["anio"].dropna().unique())
anio_default = 2023 if 2023 in anios_disponibles else int(max(anios_disponibles))
anio_sel = st.sidebar.select_slider("Año", options=anios_disponibles, value=anio_default)

metrica_label = st.sidebar.selectbox("Indicador del mapa", list(METRICAS.keys()), index=0)
metrica_col = METRICAS[metrica_label]

st.sidebar.markdown("---")
deptos_todos = sorted(df["departamento"].unique())
deptos_sel = st.sidebar.multiselect(
    "Comparar departamentos en el tiempo",
    deptos_todos,
    default=["PUNO", "AREQUIPA", "LIMA METROPOLITANA 1/"],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ La 'línea de pobreza' y el gasto/ingreso real solo existen a nivel de "
    "región natural (Costa/Sierra/Selva), no por departamento. Cada departamento "
    "hereda el valor de su región natural — es una simplificación deliberada."
)

# ---------------------------------------------------------------------------
# TÍTULO Y KPIs
# ---------------------------------------------------------------------------
st.title("Pobreza y costo de vida real por región del Perú")
st.markdown('<div class="faja"></div>', unsafe_allow_html=True)
st.caption(
    "Cruce entre pobreza monetaria e ingreso laboral por departamento (SIRTOD-INEI) "
    "y línea de pobreza / gasto real por región natural (Informe Técnico INEI, "
    "Evolución de la Pobreza Monetaria 2015-2024)."
)

datos_anio = df_mapa[df_mapa["anio"] == anio_sel].dropna(subset=[metrica_col])

col1, col2, col3, col4 = st.columns(4)
if not datos_anio.empty:
    peor = datos_anio.loc[datos_anio[metrica_col].idxmax() if metrica_col in ESCALAS_INVERTIDAS else datos_anio[metrica_col].idxmin()]
    mejor = datos_anio.loc[datos_anio[metrica_col].idxmin() if metrica_col in ESCALAS_INVERTIDAS else datos_anio[metrica_col].idxmax()]
    with col1:
        kpi_card("Promedio nacional", f"{datos_anio[metrica_col].mean():,.1f}")
    with col2:
        kpi_card("Peor situación", peor["departamento"].title(), f"{peor[metrica_col]:,.1f}")
    with col3:
        kpi_card("Mejor situación", mejor["departamento"].title(), f"{mejor[metrica_col]:,.1f}", positivo=True)
    with col4:
        kpi_card("Departamentos con dato", f"{datos_anio.shape[0]} / 25")
else:
    st.warning(f"No hay datos de '{metrica_label}' para el año {anio_sel}.")

# ---------------------------------------------------------------------------
# MAPA CHOROPLETH
# ---------------------------------------------------------------------------
st.subheader(f"{metrica_label} — {anio_sel}")

if not datos_anio.empty:
    escala = ESCALA_SOLO_ROJO if metrica_col in ESCALAS_INVERTIDAS else ESCALA_ROJO_VERDE
    fig_mapa = px.choropleth(
        datos_anio,
        geojson=geojson,
        locations="dep_geojson",
        featureidkey="properties.NOMBDEP",
        color=metrica_col,
        color_continuous_scale=escala,
        hover_name="departamento",
        hover_data={
            "dep_geojson": False,
            "pobreza_total_pct": ":.1f",
            "ingreso_laboral_soles": ":.0f",
            "linea_pobreza_total_soles": ":.0f",
            metrica_col: ":.1f",
        },
        labels={metrica_col: metrica_label},
    )
    fig_mapa.update_geos(fitbounds="locations", visible=False)
    fig_mapa.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=520,
        font_family="IBM Plex Sans", paper_bgcolor=COLOR_BG,
    )
    fig_mapa.update_coloraxes(
        colorbar=dict(
            tickfont=dict(family="IBM Plex Mono", size=12, color=COLOR_INK),
            title_font=dict(family="IBM Plex Sans", size=13, color=COLOR_INK),
            outlinewidth=0,
        )
    )
    st.plotly_chart(fig_mapa, use_container_width=True)
else:
    st.info("Prueba con otro año o indicador.")

# ---------------------------------------------------------------------------
# SERIES DE TIEMPO POR DEPARTAMENTO
# ---------------------------------------------------------------------------
st.subheader("Evolución en el tiempo")

if deptos_sel:
    df_series = df[df["departamento"].isin(deptos_sel)].dropna(subset=[metrica_col]).sort_values("anio")
    if df_series.empty:
        st.info(f"'{metrica_label}' no tiene datos disponibles para los departamentos elegidos.")
    else:
        anio_min_serie, anio_max_serie = int(df_series["anio"].min()), int(df_series["anio"].max())
        if anio_min_serie > min(anios_disponibles):
            st.caption(
                f"ℹ️ '{metrica_label}' solo tiene datos desde {anio_min_serie} en adelante "
                f"(la fuente del INEI no publica esa cifra en años anteriores)."
            )
        fig_series = px.line(
            df_series,
            x="anio",
            y=metrica_col,
            color="departamento",
            markers=True,
            color_discrete_sequence=[COLOR_COCHINILLA, COLOR_VERDE_ALTURA, COLOR_ACHIOTE, COLOR_INK, "#7A8C8A"],
            labels={metrica_col: metrica_label, "anio": "Año", "departamento": "Departamento"},
        )
        fig_series.update_layout(height=420, legend_title_text="", font_family="IBM Plex Sans", paper_bgcolor=COLOR_BG, plot_bgcolor=COLOR_SURFACE)
        fig_series.update_xaxes(range=[anio_min_serie - 0.5, anio_max_serie + 0.5], tickfont=dict(family="IBM Plex Mono"), gridcolor=COLOR_LINEA)
        fig_series.update_yaxes(tickfont=dict(family="IBM Plex Mono"), gridcolor=COLOR_LINEA)
        st.plotly_chart(fig_series, use_container_width=True)
else:
    st.info("Selecciona uno o más departamentos en la barra lateral para ver su evolución.")

# ---------------------------------------------------------------------------
# DISPERSIÓN: POBREZA VS INGRESO
# ---------------------------------------------------------------------------
st.subheader(f"Pobreza vs. ingreso laboral — {anio_sel}")

datos_scatter = df[(df["anio"] == anio_sel)].dropna(subset=["pobreza_total_pct", "ingreso_laboral_soles"])
if not datos_scatter.empty:
    fig_scatter = px.scatter(
        datos_scatter,
        x="ingreso_laboral_soles",
        y="pobreza_total_pct",
        color="region_natural",
        hover_name="departamento",
        size_max=12,
        color_discrete_map={
            "Costa": COLOR_ACHIOTE, "Sierra": COLOR_VERDE_ALTURA,
            "Selva": "#3E7C5A", "Lima Metropolitana": COLOR_COCHINILLA,
        },
        labels={
            "ingreso_laboral_soles": "Ingreso laboral promedio (S/)",
            "pobreza_total_pct": "Pobreza total (%)",
            "region_natural": "Región natural",
        },
    )
    fig_scatter.update_traces(marker=dict(size=11, line=dict(width=0.5, color="white")))
    fig_scatter.update_layout(height=440, legend_title_text="Región natural", font_family="IBM Plex Sans", paper_bgcolor=COLOR_BG, plot_bgcolor=COLOR_SURFACE)
    fig_scatter.update_xaxes(tickfont=dict(family="IBM Plex Mono"), gridcolor=COLOR_LINEA)
    fig_scatter.update_yaxes(tickfont=dict(family="IBM Plex Mono"), gridcolor=COLOR_LINEA)
    st.plotly_chart(fig_scatter, use_container_width=True)
else:
    st.info(f"No hay suficientes datos para graficar {anio_sel}.")

# ---------------------------------------------------------------------------
# TABLA
# ---------------------------------------------------------------------------
with st.expander("Ver tabla completa de datos"):
    cols_tabla = [
        "departamento", "region_natural", "anio", "pobreza_total_pct", "pobreza_extrema_pct",
        "ingreso_laboral_soles", "linea_pobreza_total_soles", "brecha_poder_adquisitivo",
        "brecha_poder_adquisitivo_pct",
    ]
    st.dataframe(
        df[df["anio"] == anio_sel][cols_tabla].sort_values("brecha_poder_adquisitivo_pct"),
        use_container_width=True,
        hide_index=True,
    )

st.markdown("---")
st.caption(
    "Fuentes: INEI-SIRTOD (pobreza monetaria e ingreso laboral por departamento) e "
    "Informe Técnico 'Perú: Evolución de la Pobreza Monetaria, 2015-2024' (línea de "
    "pobreza y gasto/ingreso real por región natural). La 'brecha de poder adquisitivo' "
    "es un indicador propio: ingreso laboral departamental menos línea de pobreza de su "
    "región natural. No es una cifra oficial del INEI."
)
