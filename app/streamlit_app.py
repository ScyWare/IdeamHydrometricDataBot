"""App Streamlit: estaciones hidrométricas IDEAM más cercanas a un punto.

Ejecutar desde la raíz del repo:
    .venv/bin/streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
import sys

import folium
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

# Permite ejecutar como script (streamlit run app/streamlit_app.py) sin instalar
# el paquete: añade la raíz del repo al path para importar `app.*`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.elevation import get_elevations
from app.stations import nearest_ideam_stations

st.set_page_config(page_title="Estaciones hidrométricas IDEAM", layout="wide")


@st.cache_data(show_spinner=False)
def _elevaciones_cache(coords: tuple[tuple[float, float], ...]) -> list[float | None]:
    """Cachea la elevación por conjunto de coordenadas (evita repetir la API)."""
    return get_elevations(list(coords))


def buscar(lat: float, lon: float, top_k: int, incluir_cerradas: bool) -> pd.DataFrame:
    """Busca estaciones, les añade altura y devuelve un DataFrame ordenado por altura."""
    estaciones = nearest_ideam_stations(lat, lon, top_k, incluir_cerradas)
    if not estaciones:
        return pd.DataFrame()

    coords = tuple((e["latitud"], e["longitud"]) for e in estaciones)
    alturas = _elevaciones_cache(coords)

    df = pd.DataFrame(estaciones)
    df["altura_m"] = alturas
    df = df.sort_values("altura_m", ascending=False, na_position="last").reset_index(drop=True)
    df.insert(0, "Seleccionar", False)
    return df


def construir_mapa(df: pd.DataFrame, lat: float, lon: float) -> folium.Map:
    """Mapa topográfico (OpenTopoMap: ríos, relieve, curvas de nivel) con marcadores."""
    m = folium.Map(
        location=[lat, lon],
        zoom_start=10,
        tiles="OpenTopoMap",
        attr="© OpenTopoMap (CC-BY-SA), © OpenStreetMap contributors",
        control_scale=True,
    )

    # Punto de entrada del usuario.
    folium.Marker(
        [lat, lon],
        tooltip="Punto de consulta",
        popup=f"Entrada<br>lat: {lat:.5f}<br>lon: {lon:.5f}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa"),
    ).add_to(m)

    # Estaciones.
    for _, row in df.iterrows():
        altura = "s/d" if pd.isna(row["altura_m"]) else f"{row['altura_m']:.0f} m"
        color = "blue" if row["activa"] else "gray"
        folium.Marker(
            [row["latitud"], row["longitud"]],
            tooltip=f"{row['codigo']} · {row['nombre']}",
            popup=folium.Popup(
                f"<b>{row['nombre']}</b><br>Código: {row['codigo']}<br>"
                f"Categoría: {row['categoria']}<br>Altura: {altura}<br>"
                f"Distancia: {row['distancia_km']:.2f} km<br>"
                f"{'Activa' if row['activa'] else 'Cerrada ' + str(row['fecha_fin_op'])}",
                max_width=280,
            ),
            icon=folium.Icon(color=color, icon="tint", prefix="fa"),
        ).add_to(m)

    # Encaja el zoom a todos los puntos.
    puntos = [[lat, lon]] + df[["latitud", "longitud"]].values.tolist()
    m.fit_bounds(puntos, padding=(30, 30))
    return m


def grafico_altura(df: pd.DataFrame):
    """Barras horizontales de estaciones ordenadas por altura (código, nombre, altura)."""
    d = df.dropna(subset=["altura_m"]).copy()
    if d.empty:
        return None
    d["etiqueta"] = d["codigo"] + " · " + d["nombre"].str.replace(r"\s*\[\d+\]", "", regex=True)
    d = d.sort_values("altura_m", ascending=True)
    fig = px.bar(
        d,
        x="altura_m",
        y="etiqueta",
        orientation="h",
        text="altura_m",
        labels={"altura_m": "Altura (m s. n. m.)", "etiqueta": ""},
        hover_data={"codigo": True, "nombre": True, "distancia_km": ":.2f", "etiqueta": False},
    )
    fig.update_traces(texttemplate="%{text:.0f} m", textposition="outside", cliponaxis=False)
    fig.update_layout(height=max(300, 60 * len(d)), margin=dict(l=10, r=10, t=30, b=10))
    return fig


# --------------------------------------------------------------------- Sidebar
st.sidebar.header("⚙️ Configuración")

lat = st.sidebar.number_input("Latitud", value=5.6947, format="%.6f")
lon = st.sidebar.number_input("Longitud", value=-76.6611, format="%.6f")
top_k = st.sidebar.slider("Top K estaciones más cercanas", 1, 50, 5)
incluir_cerradas = st.sidebar.checkbox("Incluir estaciones cerradas", value=True)

if st.sidebar.button("🔎 Buscar estaciones", use_container_width=True):
    with st.spinner("Buscando estaciones y consultando alturas…"):
        st.session_state["df"] = buscar(lat, lon, top_k, incluir_cerradas)
        st.session_state["punto"] = (lat, lon)

st.sidebar.divider()
st.sidebar.subheader("⬇️ Descarga DHIME")
variable_id = st.sidebar.number_input("variable_id", value=84, step=1,
                                       help="p.ej. 84 = precipitación diaria")
date_ini = st.sidebar.text_input("Fecha inicio (dd/mm/aaaa)", value="01/01/2000")
date_fin = st.sidebar.text_input("Fecha fin (dd/mm/aaaa)", value="01/01/2026")
download_path = st.sidebar.text_input("Carpeta destino", value="app/data")


# ------------------------------------------------------------------------ Main
st.title("💧 Estaciones hidrométricas IDEAM (DHIME)")

df = st.session_state.get("df")
if df is None:
    st.info("Configura latitud, longitud y Top K en la barra lateral, y pulsa **Buscar estaciones**.")
    st.stop()

if df.empty:
    st.warning("No se encontraron estaciones hidrométricas con esos parámetros.")
    st.stop()

punto = st.session_state.get("punto", (lat, lon))

col_mapa, col_graf = st.columns([3, 2])

with col_mapa:
    st.subheader("🗺️ Mapa (relieve y ríos)")
    st_folium(
        construir_mapa(df, punto[0], punto[1]),
        use_container_width=True,
        height=520,
        returned_objects=[],  # solo visualización: evita reruns innecesarios
    )

with col_graf:
    st.subheader("📊 Estaciones por altura")
    fig = grafico_altura(df)
    if fig is None:
        st.caption("Sin datos de altura para graficar.")
    else:
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("✅ Selecciona las estaciones a descargar")

editado = st.data_editor(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Seleccionar": st.column_config.CheckboxColumn(required=True),
        "distancia_km": st.column_config.NumberColumn("Dist. (km)", format="%.2f"),
        "altura_m": st.column_config.NumberColumn("Altura (m)", format="%.0f"),
        "codigo": "Código",
        "nombre": "Nombre",
        "categoria": "Categoría",
        "municipio": "Municipio",
        "departamento": "Departamento",
        "activa": "Activa",
    },
    column_order=[
        "Seleccionar", "codigo", "nombre", "altura_m", "distancia_km",
        "categoria", "municipio", "departamento", "activa", "fecha_fin_op",
    ],
    disabled=[c for c in df.columns if c != "Seleccionar"],
    key="editor",
)

seleccionadas = editado[editado["Seleccionar"]]
codigos = seleccionadas["codigo"].tolist()

st.caption(f"{len(codigos)} estación(es) seleccionada(s): {', '.join(codigos) if codigos else '—'}")

if st.button("⬇️ Descargar datos de las seleccionadas", type="primary", disabled=not codigos):
    from app.downloader import descargar_estaciones

    with st.spinner(f"Descargando {len(codigos)} estación(es) desde DHIME (abre Chrome)…"):
        resultados = descargar_estaciones(
            codigos=codigos,
            download_path=download_path,
            variable_id=int(variable_id),
            date_ini=date_ini,
            date_fin=date_fin,
        )
    st.success("Descarga finalizada.")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Código": r.request.station_code,
                    "Estado": r.status,
                    "Mensaje": r.message,
                    "CSV final": str(r.csv_final),
                }
                for r in resultados
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
