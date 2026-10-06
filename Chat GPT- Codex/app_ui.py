"""
Dashboard Streamlit para ejecutar el rutero inteligente.

Ejecucion:
    streamlit run app_ui.py
"""

from __future__ import annotations

from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from dummy_data import OUTPUT_FILE, generar_datos_dummy
from etl_features import FEATURE_STORE_PATH, ScoreWeights, ejecutar_pipeline_etl
from mlp_model import entrenar_mlp
from route_optimizer import optimizar_ruta


st.set_page_config(page_title="Rutero Inteligente", layout="wide")


def asegurar_datos_demo() -> Path:
    """Crea datos demo si aun no existen."""
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    if not OUTPUT_FILE.exists():
        generar_datos_dummy().to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    return OUTPUT_FILE


def dibujar_mapa(resultado_ruta: dict) -> folium.Map:
    """Renderiza el mapa con marcadores y linea de ruta."""
    puntos = resultado_ruta["puntos_mapa"]
    origen = resultado_ruta["origen"]
    centro = [origen["latitud"], origen["longitud"]]
    mapa = folium.Map(location=centro, zoom_start=12, tiles="OpenStreetMap")

    coordenadas = []
    for punto in puntos:
        lat_lon = [punto["latitud"], punto["longitud"]]
        coordenadas.append(lat_lon)
        es_origen = punto["cliente_id"] == "ORIGEN"
        folium.Marker(
            location=lat_lon,
            tooltip=punto["cliente_nombre"],
            popup=(
                f"{punto['cliente_nombre']}<br>"
                f"Prioridad: {punto.get('probabilidad_prioridad_visita', 0):.2f}"
            ),
            icon=folium.Icon(color="blue" if es_origen else "green", icon="home" if es_origen else "user"),
        ).add_to(mapa)

    if len(coordenadas) > 1:
        folium.PolyLine(coordenadas, color="#2563eb", weight=4, opacity=0.85).add_to(mapa)

    return mapa


st.title("Rutero Inteligente para Ejecutivos")
st.caption("ETL + Feature Store + MLP + OR-Tools + mapa interactivo")

with st.sidebar:
    st.header("Configuracion")
    archivo_demo = asegurar_datos_demo()
    archivo_subido = st.file_uploader("CSV o Excel historico", type=["csv", "xlsx", "xls"])
    usar_demo = st.checkbox("Usar datos demo de Ecuador", value=True)

    st.subheader("Pesos de scoring")
    peso_dia = st.slider("Dia de semana", 0.0, 1.0, 0.40, 0.05)
    peso_semana = st.slider("Semana ISO", 0.0, 1.0, 0.25, 0.05)
    peso_mes = st.slider("Mes", 0.0, 1.0, 0.20, 0.05)
    peso_monto = st.slider("Monto", 0.0, 1.0, 0.15, 0.05)

    st.subheader("Optimizacion")
    peso_prioridad = st.slider("Peso de prioridad en la ruta", 0.0, 0.95, 0.35, 0.05)
    lat_inicio = st.number_input("Latitud inicio", value=-0.2298, format="%.6f")
    lon_inicio = st.number_input("Longitud inicio", value=-78.5249, format="%.6f")
    ejecutar = st.button("Ejecutar pipeline y ruta", type="primary")

if archivo_subido and not usar_demo:
    ruta_entrada = Path("data") / archivo_subido.name
    ruta_entrada.parent.mkdir(exist_ok=True)
    ruta_entrada.write_bytes(archivo_subido.getbuffer())
else:
    ruta_entrada = archivo_demo

col_a, col_b, col_c = st.columns(3)
col_a.metric("Archivo de entrada", ruta_entrada.name)
col_b.metric("Feature Store", FEATURE_STORE_PATH.name)
col_c.metric("Motor de rutas", "Google OR-Tools")

if ejecutar:
    try:
        pesos = ScoreWeights(
            dia_semana=peso_dia,
            semana_iso=peso_semana,
            mes=peso_mes,
            monto=peso_monto,
        )

        with st.spinner("Ejecutando ETL, scoring y Feature Store..."):
            feature_store = ejecutar_pipeline_etl(ruta_entrada, weights=pesos)

        with st.spinner("Entrenando MLP y calculando prioridad de visita..."):
            _, clientes_priorizados, metricas = entrenar_mlp(feature_store)

        with st.spinner("Optimizando ruta priorizada con OR-Tools..."):
            resultado = optimizar_ruta(
                clientes_priorizados,
                lat_inicio=lat_inicio,
                lon_inicio=lon_inicio,
                peso_prioridad=peso_prioridad,
            )

        st.success("Pipeline ejecutado correctamente.")

        m1, m2, m3 = st.columns(3)
        m1.metric("Clientes en ruta", resultado["resumen"]["total_clientes"])
        m2.metric("Distancia aprox.", f"{resultado['resumen']['distancia_aproximada_km']} km")
        m3.metric("MAE modelo", f"{metricas['mae_entrenamiento']:.3f}")

        tabla = pd.DataFrame(resultado["ruta"])
        columnas_tabla = [
            "orden_visita",
            "cliente_id",
            "cliente_nombre",
            "zona",
            "probabilidad_prioridad_visita",
            "score_estadistico",
            "latitud",
            "longitud",
        ]
        columnas_visibles = [col for col in columnas_tabla if col in tabla.columns]

        st.subheader("Clientes ordenados por secuencia optima")
        st.dataframe(tabla[columnas_visibles], use_container_width=True, hide_index=True)

        st.subheader("Mapa de ruta")
        st_folium(dibujar_mapa(resultado), width=None, height=560)

        with st.expander("Ver Feature Store simulado"):
            st.dataframe(clientes_priorizados, use_container_width=True, hide_index=True)

    except Exception as exc:
        st.error(f"No se pudo ejecutar el pipeline: {exc}")
else:
    st.info("Configura los parametros y pulsa el boton para generar la ruta.")
    vista_previa = pd.read_csv(ruta_entrada) if ruta_entrada.suffix.lower() == ".csv" else pd.read_excel(ruta_entrada)
    st.dataframe(vista_previa.head(10), use_container_width=True, hide_index=True)
