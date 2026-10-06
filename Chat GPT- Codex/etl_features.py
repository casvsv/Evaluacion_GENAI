"""
ETL, Feature Builder, Scoring y Feature Store simulado.

Este modulo transforma transacciones historicas en una tabla por cliente lista
para entrenamiento de IA y optimizacion de rutas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd


FEATURE_STORE_PATH = Path("data/feature_store_clientes.csv")


@dataclass(frozen=True)
class ScoreWeights:
    """Pesos configurables para combinar patrones temporales."""

    dia_semana: float = 0.40
    semana_iso: float = 0.25
    mes: float = 0.20
    monto: float = 0.15

    def normalizados(self) -> Dict[str, float]:
        total = self.dia_semana + self.semana_iso + self.mes + self.monto
        if total <= 0:
            raise ValueError("La suma de pesos debe ser mayor que cero.")
        return {
            "score_dia_semana": self.dia_semana / total,
            "score_semana_iso": self.semana_iso / total,
            "score_mes": self.mes / total,
            "score_monto": self.monto / total,
        }


def cargar_datos(ruta_archivo: str | Path) -> pd.DataFrame:
    """Carga un archivo CSV o Excel con transacciones historicas."""
    ruta = Path(ruta_archivo)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")

    if ruta.suffix.lower() == ".csv":
        df = pd.read_csv(ruta)
    elif ruta.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(ruta)
    else:
        raise ValueError("Formato no soportado. Use CSV, XLSX o XLS.")

    columnas_requeridas = {
        "fecha",
        "cliente_id",
        "cliente_nombre",
        "latitud",
        "longitud",
        "monto",
    }
    faltantes = columnas_requeridas.difference(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas: {sorted(faltantes)}")

    return df


def limpiar_y_enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia datos, conserva lunes a viernes y agrega variables temporales."""
    df_limpio = df.copy()
    df_limpio["fecha"] = pd.to_datetime(df_limpio["fecha"], errors="coerce")
    df_limpio = df_limpio.dropna(subset=["fecha", "cliente_id", "latitud", "longitud"])
    df_limpio["monto"] = pd.to_numeric(df_limpio["monto"], errors="coerce").fillna(0)

    df_limpio["dia_semana"] = df_limpio["fecha"].dt.dayofweek
    df_limpio = df_limpio[df_limpio["dia_semana"].between(0, 4)].copy()

    df_limpio["nombre_dia"] = df_limpio["fecha"].dt.day_name(locale=None)
    df_limpio["semana_iso"] = df_limpio["fecha"].dt.isocalendar().week.astype(int)
    df_limpio["mes"] = df_limpio["fecha"].dt.month
    df_limpio["es_cobro"] = (df_limpio.get("tipo_transaccion", "") == "cobro").astype(int)
    df_limpio["es_pedido"] = (df_limpio.get("tipo_transaccion", "") == "pedido").astype(int)
    df_limpio["estado_completado"] = (df_limpio.get("estado", "") == "completado").astype(int)

    return df_limpio.reset_index(drop=True)


def _score_por_bloque(df: pd.DataFrame, columna_bloque: str) -> pd.Series:
    """Calcula un score cliente-bloque a partir de frecuencia y monto."""
    actividad = (
        df.groupby(["cliente_id", columna_bloque])
        .agg(frecuencia=("cliente_id", "size"), monto_total=("monto", "sum"))
        .reset_index()
    )
    actividad["actividad"] = actividad["frecuencia"] + np.log1p(actividad["monto_total"])
    score_cliente = actividad.groupby("cliente_id")["actividad"].max()
    maximo = score_cliente.max()
    if maximo == 0 or pd.isna(maximo):
        return score_cliente * 0
    return score_cliente / maximo


def construir_feature_store(
    df_enriquecido: pd.DataFrame,
    weights: ScoreWeights | None = None,
    output_path: str | Path = FEATURE_STORE_PATH,
) -> pd.DataFrame:
    """Agrega datos por cliente, calcula scores y persiste el Feature Store."""
    if df_enriquecido.empty:
        raise ValueError("No hay datos laborables para construir features.")

    weights = weights or ScoreWeights()
    pesos = weights.normalizados()

    base = (
        df_enriquecido.groupby("cliente_id")
        .agg(
            cliente_nombre=("cliente_nombre", "first"),
            zona=("zona", "first") if "zona" in df_enriquecido.columns else ("cliente_id", "first"),
            latitud=("latitud", "mean"),
            longitud=("longitud", "mean"),
            total_transacciones=("cliente_id", "size"),
            monto_total=("monto", "sum"),
            monto_promedio=("monto", "mean"),
            tasa_cobros=("es_cobro", "mean"),
            tasa_pedidos=("es_pedido", "mean"),
            tasa_completados=("estado_completado", "mean"),
            ultimo_movimiento=("fecha", "max"),
        )
        .reset_index()
    )

    scores = pd.DataFrame({"cliente_id": base["cliente_id"]})
    scores["score_dia_semana"] = scores["cliente_id"].map(_score_por_bloque(df_enriquecido, "dia_semana")).fillna(0)
    scores["score_semana_iso"] = scores["cliente_id"].map(_score_por_bloque(df_enriquecido, "semana_iso")).fillna(0)
    scores["score_mes"] = scores["cliente_id"].map(_score_por_bloque(df_enriquecido, "mes")).fillna(0)

    monto_max = base["monto_total"].max()
    base["score_monto"] = 0 if monto_max == 0 else base["monto_total"] / monto_max

    feature_store = base.merge(scores, on="cliente_id", how="left")
    feature_store["score_estadistico"] = (
        feature_store["score_dia_semana"] * pesos["score_dia_semana"]
        + feature_store["score_semana_iso"] * pesos["score_semana_iso"]
        + feature_store["score_mes"] * pesos["score_mes"]
        + feature_store["score_monto"] * pesos["score_monto"]
    )
    feature_store["score_estadistico"] = feature_store["score_estadistico"].clip(0, 1)
    feature_store = feature_store.sort_values("score_estadistico", ascending=False).reset_index(drop=True)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    feature_store.to_csv(output, index=False, encoding="utf-8")
    return feature_store


def ejecutar_pipeline_etl(
    ruta_archivo: str | Path,
    weights: ScoreWeights | None = None,
    output_path: str | Path = FEATURE_STORE_PATH,
) -> pd.DataFrame:
    """Ejecuta carga, limpieza, enriquecimiento y Feature Store."""
    df = cargar_datos(ruta_archivo)
    df_enriquecido = limpiar_y_enriquecer(df)
    return construir_feature_store(df_enriquecido, weights=weights, output_path=output_path)
