"""
Dashboard de demostración — TFM Fernanda Jaramillo
Pronóstico de demanda (DeepAR v9) y optimización de pedidos (newsvendor)
Corporación Favorita — familia DAIRY, Pichincha

Corre en local (no en Colab), para no depender de túneles ni de Drive montado
durante la defensa. Requiere los archivos en la carpeta data/ (ver README abajo).

Diseño institucional: colores y tipografía tomados de la plantilla oficial de
PowerPoint de la Universidad Europea (Plantilla_ppt_UE_BigData.pptx), extraídos
directamente de ppt/theme/theme1.xml (esquema de color "UEM"). El rosa (accent4,
#FFAFAA) es el más cercano disponible en esa plantilla — no existe un magenta
puro en el esquema oficial, así que este es el sustituto real, no una elección
arbitraria mía.

Ejecutar con:  streamlit run dashboard.py
"""

import base64
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --- Paleta institucional UEM (ppt/theme/theme1.xml, esquema "UEM") ---
ROJO = "#FF3228"        # accent1
AZUL = "#2D41B4"        # accent2
TURQUESA = "#23B4AA"    # accent3
ROSA = "#FFAFAA"        # accent4 (rosa/coral claro — no hay magenta en la plantilla oficial)
ROSA_BORDE = "#FF5A50"  # accent5
OSCURO = "#1E1E1E"      # dk1
GRIS_OSCURO = "#504B4B" # dk2 / accent6
GRIS_CLARO = "#D2D1D1"  # lt2
FONDO_SIDEBAR = "#F9F8F7"
VERDE_MEJORA = "#1D9E75"  # para deltas de costo positivos (reducción)

st.set_page_config(
    page_title="TFM — Pronóstico y Newsvendor (Favorita, DAIRY)",
    layout="wide",
)

DATA_DIR = Path(__file__).parent / "data"
ASSETS_DIR = Path(__file__).parent / "assets"

NIVELES = [0.02, 0.1, 0.25, 0.5, 0.75, 0.9, 0.98]
COLS_V9 = {q: f"v9_q{q}" for q in NIVELES}


@st.cache_data
def cargar_datos():
    comp = pd.read_parquet(DATA_DIR / "comparacion_completa_v2.parquet")
    fechas = pd.read_csv(DATA_DIR / "time_idx_fechas.csv", parse_dates=["date"])
    metadata = pd.read_csv(DATA_DIR / "metadata_series.csv")
    resumen_newsvendor = pd.read_csv(DATA_DIR / "resultados_newsvendor_resumen.csv")

    # comp guarda store_nbr/item_nbr como texto (así se evaluó en Colab, ver Fav_d7/Fav_d12,
    # celda de casteo a str antes de construir el TimeSeriesDataSet); metadata los trae como
    # número entero (para que las listas de la barra lateral ordenen bien). Igualamos aquí para
    # que el filtro de la serie seleccionada sí encuentre coincidencias.
    comp["store_nbr"] = comp["store_nbr"].astype(str)
    comp["item_nbr"] = comp["item_nbr"].astype(str)
    metadata["store_nbr"] = metadata["store_nbr"].astype(int)
    metadata["item_nbr"] = metadata["item_nbr"].astype(int)

    comp = comp.merge(fechas, on="time_idx", how="left")
    return comp, metadata, resumen_newsvendor


@st.cache_data
def cargar_logo_b64():
    logo_path = ASSETS_DIR / "logo_uem.png"
    if not logo_path.exists():
        return None
    return base64.b64encode(logo_path.read_bytes()).decode("ascii")


def cuantil_interpolado(df, nivel):
    if nivel in NIVELES:
        return df[COLS_V9[nivel]].values
    inferiores = [n for n in NIVELES if n < nivel]
    superiores = [n for n in NIVELES if n > nivel]
    n_inf, n_sup = max(inferiores), min(superiores)
    y_inf, y_sup = df[COLS_V9[n_inf]].values, df[COLS_V9[n_sup]].values
    peso = (nivel - n_inf) / (n_sup - n_inf)
    return y_inf + peso * (y_sup - y_inf)


def costo_newsvendor(actual, Q, Cu, Co):
    diferencia = actual - Q
    return np.where(diferencia > 0, Cu * diferencia, Co * (-diferencia))


def tarjeta_costo(titulo, valor, color_borde, delta_texto=None):
    """Tarjeta de costo con borde de color a la izquierda, igual que el mockup aprobado."""
    delta_html = ""
    if delta_texto is not None:
        delta_html = f'<div style="font-size:12px;color:{VERDE_MEJORA};margin-top:2px;">{delta_texto}</div>'
    return f"""
    <div style="background:#FFFFFF;border-radius:8px;border:0.5px solid #DDD;
                border-left:4px solid {color_borde};padding:12px 14px;">
      <div style="font-size:12px;color:{GRIS_OSCURO};">{titulo}</div>
      <div style="font-size:22px;font-weight:700;color:{OSCURO};">{valor}</div>
      {delta_html}
    </div>
    """


# --- CSS institucional ---
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Century Gothic', 'Futura', 'Poppins', sans-serif;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {FONDO_SIDEBAR};
        border-right: 0.5px solid #DDD;
    }}
    .uem-sidebar-label {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        color: {ROJO};
        text-transform: uppercase;
        margin-top: 18px;
        margin-bottom: 6px;
    }}
    div[data-testid="stSelectbox"] > div, div[data-testid="stSelectSlider"] > div {{
        border-radius: 6px;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Cabecera institucional (logo + título, franja roja inferior) ---
_logo_b64 = cargar_logo_b64()
_logo_img_tag = (
    f'<img src="data:image/png;base64,{_logo_b64}" style="height:40px;object-fit:contain;" alt="logo UEM"/>'
    if _logo_b64
    else '<div style="font-size:13px;color:#888;">[logo no encontrado en assets/logo_uem.png]</div>'
)
st.markdown(
    f"""
    <div style="background:#FFFFFF;padding:14px 18px;margin:-1rem -1rem 1.2rem -1rem;
                display:flex;align-items:center;justify-content:space-between;
                border-bottom:3px solid {ROJO};">
      {_logo_img_tag}
      <div style="text-align:right;">
        <div style="font-size:15px;font-weight:700;color:{OSCURO};letter-spacing:0.3px;">
          PRONÓSTICO DE DEMANDA Y OPTIMIZACIÓN DE PEDIDOS
        </div>
        <div style="font-size:12px;color:{GRIS_OSCURO};">
          Corporación Favorita — familia DAIRY, Pichincha · Modelo final: DeepAR v9 ·
          TFM, Máster en Análisis de Datos Masivos
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    comp, metadata, resumen_newsvendor = cargar_datos()
except FileNotFoundError as e:
    st.error(
        "Falta un archivo en la carpeta data/. Revisa que estén los cuatro archivos "
        "indicados en el README (comparacion_completa_v2.parquet, time_idx_fechas.csv, "
        "metadata_series.csv, resultados_newsvendor_resumen.csv).\n\n"
        f"Detalle: {e}"
    )
    st.stop()

# --- Sidebar: selección de serie ---
st.sidebar.markdown('<div class="uem-sidebar-label">Selección de serie</div>', unsafe_allow_html=True)

ciudades = sorted(metadata["city"].unique())
ciudad_sel = st.sidebar.selectbox("Ciudad", ciudades)

tiendas_disp = sorted(metadata.loc[metadata["city"] == ciudad_sel, "store_nbr"].unique())
tienda_sel = st.sidebar.selectbox("Tienda (store_nbr)", tiendas_disp)

productos_disp = sorted(metadata.loc[metadata["store_nbr"] == tienda_sel, "item_nbr"].unique())
producto_sel = st.sidebar.selectbox("Producto (item_nbr)", productos_disp)

info_serie = metadata[
    (metadata["store_nbr"] == tienda_sel) & (metadata["item_nbr"] == producto_sel)
].iloc[0]
st.sidebar.markdown(f"**Familia:** {info_serie['family']} — **Clase:** {info_serie['class']}")
st.sidebar.markdown(f"**Tipo de tienda:** {info_serie['store_type']} — **Clúster:** {info_serie['cluster']}")

st.sidebar.markdown('<div class="uem-sidebar-label">Escenario de inventario (newsvendor)</div>', unsafe_allow_html=True)
escenario_sel = st.sidebar.select_slider(
    "Razón crítica (≈ tasa de margen)",
    options=[0.20, 0.25, 0.35],
    value=0.25,
    help=(
        "Escenario plausible de sensibilidad alrededor del margen corporativo de "
        "Corporación Favorita (25%, 2020) — no es el margen medido de la categoría "
        "DAIRY. Ver Notas_Sustento_Teorico_TFM.md, punto 10."
    ),
)

# --- Filtrar la serie seleccionada ---
# tienda_sel/producto_sel vienen de metadata (número); comp los tiene como texto tras el casteo
# de cargar_datos() — se convierten aquí para que la comparación funcione.
serie = comp[
    (comp["store_nbr"] == str(tienda_sel)) & (comp["item_nbr"] == str(producto_sel))
].sort_values("date").copy()

if serie.empty:
    st.warning("Esta combinación tienda-producto no tiene predicciones en el conjunto de test evaluado.")
    st.stop()

# --- Gráfico de pronóstico con bandas de cuantiles ---
st.subheader(f"Pronóstico DeepAR v9 — Tienda {tienda_sel}, Producto {producto_sel}")

fig = go.Figure()

# banda ancha (2%-98%) — azul institucional
fig.add_trace(go.Scatter(x=serie["date"], y=serie["v9_q0.02"], line=dict(width=0),
                          showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=serie["date"], y=serie["v9_q0.98"], line=dict(width=0),
                          fill="tonexty", fillcolor="rgba(45,65,180,0.12)",
                          name="Intervalo 96% (q0.02–q0.98)"))
# banda angosta (10%-90%) — turquesa institucional
fig.add_trace(go.Scatter(x=serie["date"], y=serie["v9_q0.1"], line=dict(width=0),
                          showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=serie["date"], y=serie["v9_q0.9"], line=dict(width=0),
                          fill="tonexty", fillcolor="rgba(35,180,170,0.25)",
                          name="Intervalo 80% (q0.10–q0.90)"))

fig.add_trace(go.Scatter(x=serie["date"], y=serie["v9_q0.5"],
                          line=dict(color=AZUL, width=2.5), name="Mediana DeepAR v9"))
fig.add_trace(go.Scatter(x=serie["date"], y=serie["actual"],
                          line=dict(color=OSCURO, width=1.5, dash="dot"), name="Venta real"))
fig.add_trace(go.Scatter(x=serie["date"], y=serie["pred_naive"],
                          line=dict(color=GRIS_OSCURO, width=1, dash="dash"), name="Baseline naive"))

fig.update_layout(
    hovermode="x unified", yaxis_title="Unidades vendidas", xaxis_title="Fecha",
    legend=dict(orientation="h", y=-0.25), margin=dict(t=10),
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    font=dict(color=OSCURO),
)
st.plotly_chart(fig, use_container_width=True)

# --- Recomendación de pedido (newsvendor) para la serie seleccionada ---
st.subheader("Recomendación de pedido (newsvendor)")

m = escenario_sel
Cu = m / (1 - m)
Co = 1.0

serie["pedido_newsvendor"] = cuantil_interpolado(serie, m)
serie["costo_naive"] = costo_newsvendor(serie["actual"].values, serie["pred_naive"].values, Cu, Co)
serie["costo_mediana"] = costo_newsvendor(serie["actual"].values, serie["v9_q0.5"].values, Cu, Co)
serie["costo_newsvendor"] = costo_newsvendor(serie["actual"].values, serie["pedido_newsvendor"].values, Cu, Co)

costo_naive_prom = serie["costo_naive"].mean()
costo_mediana_prom = serie["costo_mediana"].mean()
costo_newsvendor_prom = serie["costo_newsvendor"].mean()

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(tarjeta_costo("Costo promedio — naive", f"{costo_naive_prom:.2f}", GRIS_OSCURO), unsafe_allow_html=True)
with col2:
    delta_mediana = (costo_mediana_prom / costo_naive_prom - 1) * 100
    st.markdown(
        tarjeta_costo("Costo promedio — mediana DeepAR", f"{costo_mediana_prom:.2f}", AZUL,
                      f"{delta_mediana:.1f}% vs. naive"),
        unsafe_allow_html=True,
    )
with col3:
    delta_newsvendor = (costo_newsvendor_prom / costo_naive_prom - 1) * 100
    st.markdown(
        tarjeta_costo("Costo promedio — newsvendor", f"{costo_newsvendor_prom:.2f}", ROJO,
                      f"{delta_newsvendor:.1f}% vs. naive"),
        unsafe_allow_html=True,
    )

st.markdown("")  # espaciado tras las tarjetas HTML
st.caption(
    "Costos en unidades relativas (Co=1), no en dólares — ver Notas_Sustento_Teorico_TFM.md, "
    "punto 10. Calculados solo sobre esta serie, pueden diferir bastante del agregado de abajo "
    "según el volumen de esta combinación tienda-producto."
)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=serie["date"], y=serie["actual"], name="Venta real",
                           line=dict(color=OSCURO)))
fig2.add_trace(go.Scatter(x=serie["date"], y=serie["pedido_newsvendor"],
                           name=f"Pedido recomendado (razón crítica {m})",
                           line=dict(color=TURQUESA, dash="dot")))
fig2.update_layout(
    yaxis_title="Unidades", xaxis_title="Fecha", hovermode="x unified", margin=dict(t=10),
    plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
    font=dict(color=OSCURO),
)
st.plotly_chart(fig2, use_container_width=True)

# --- Resultado agregado, para dar contexto más allá de esta serie ---
st.subheader("Resultado agregado (las 3.981 series del conjunto de test)")
st.dataframe(
    resumen_newsvendor.style.format(
        {c: "{:.3f}" for c in resumen_newsvendor.select_dtypes("number").columns}
    ),
    use_container_width=True,
)
st.caption(
    "El valor de leer el cuantil correcto (columna de reducción newsvendor vs. mediana) "
    "cae a medida que el escenario se acerca a 0,5 — consistente con la teoría del newsvendor."
)

# --- Pie de página institucional ---
st.markdown(
    f"""
    <div style="margin-top:2rem;padding:10px 4px 4px 4px;border-top:0.5px solid #DDD;
                display:flex;justify-content:space-between;align-items:center;">
      <div style="display:flex;gap:3px;">
        <div style="width:8px;height:8px;border:1.5px solid {ROJO};"></div>
        <div style="width:8px;height:8px;border:1.5px solid {AZUL};"></div>
        <div style="width:8px;height:8px;border:1.5px solid {ROSA};"></div>
        <div style="width:8px;height:8px;border:1.5px solid {TURQUESA};"></div>
      </div>
      <div style="font-size:11px;color:#888;">
        Universidad Europea de Madrid · Máster en Análisis de Datos Masivos
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
