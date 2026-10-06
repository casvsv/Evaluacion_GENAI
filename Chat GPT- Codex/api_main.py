"""
API FastAPI para ejecutar el pipeline y optimizar rutas.

Ejecucion:
    uvicorn api_main:app --reload
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from etl_features import FEATURE_STORE_PATH, ScoreWeights, ejecutar_pipeline_etl
from mlp_model import entrenar_mlp
from route_optimizer import optimizar_ruta


DATA_DEFAULT = Path("data/clientes_historicos_ecuador.csv")

app = FastAPI(
    title="Rutero Inteligente para Ejecutivos",
    version="1.0.0",
    description="ETL, Feature Store, MLP y optimizacion de rutas con OR-Tools.",
)


class ClienteInput(BaseModel):
    cliente_id: str
    cliente_nombre: str
    latitud: float
    longitud: float
    zona: Optional[str] = "Sin zona"
    probabilidad_prioridad_visita: Optional[float] = Field(default=None, ge=0, le=1)


class OptimizeRouteRequest(BaseModel):
    ruta_archivo: Optional[str] = Field(default=str(DATA_DEFAULT))
    zona: Optional[str] = None
    clientes: Optional[List[ClienteInput]] = None
    lat_inicio: Optional[float] = None
    lon_inicio: Optional[float] = None
    peso_prioridad: float = Field(default=0.35, ge=0, le=0.95)
    peso_dia_semana: float = 0.40
    peso_semana_iso: float = 0.25
    peso_mes: float = 0.20
    peso_monto: float = 0.15


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/v1/optimize_route")
def optimize_route(payload: OptimizeRouteRequest) -> dict:
    """Entrena el MLP si hace falta y devuelve la ruta optima de visita."""
    try:
        if payload.clientes:
            clientes_df = pd.DataFrame([cliente.model_dump() for cliente in payload.clientes])
            if clientes_df["probabilidad_prioridad_visita"].isna().any():
                clientes_df["probabilidad_prioridad_visita"] = 0.5
            resultado = optimizar_ruta(
                clientes_df,
                lat_inicio=payload.lat_inicio,
                lon_inicio=payload.lon_inicio,
                peso_prioridad=payload.peso_prioridad,
            )
            return {"origen_datos": "clientes_payload", **resultado}

        pesos = ScoreWeights(
            dia_semana=payload.peso_dia_semana,
            semana_iso=payload.peso_semana_iso,
            mes=payload.peso_mes,
            monto=payload.peso_monto,
        )
        feature_store = ejecutar_pipeline_etl(payload.ruta_archivo, weights=pesos, output_path=FEATURE_STORE_PATH)
        _, clientes_priorizados, metricas = entrenar_mlp(feature_store)

        if payload.zona:
            clientes_priorizados = clientes_priorizados[
                clientes_priorizados["zona"].astype(str).str.lower() == payload.zona.lower()
            ].copy()

        resultado = optimizar_ruta(
            clientes_priorizados,
            lat_inicio=payload.lat_inicio,
            lon_inicio=payload.lon_inicio,
            peso_prioridad=payload.peso_prioridad,
        )
        return {
            "origen_datos": str(payload.ruta_archivo),
            "metricas_modelo": metricas,
            "feature_store": str(FEATURE_STORE_PATH),
            **resultado,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
