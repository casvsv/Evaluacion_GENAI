"""
Modelo MLP para estimar probabilidad de prioridad de visita.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder


MODEL_PATH = Path("models/mlp_prioridad_visita.joblib")

NUMERIC_FEATURES = [
    "total_transacciones",
    "monto_total",
    "monto_promedio",
    "tasa_cobros",
    "tasa_pedidos",
    "tasa_completados",
    "score_dia_semana",
    "score_semana_iso",
    "score_mes",
    "score_monto",
    "score_estadistico",
]
CATEGORICAL_FEATURES = ["zona"]


def _crear_target_prioridad(feature_store: pd.DataFrame) -> pd.Series:
    """
    Crea un objetivo supervisado simulado cuando no existe etiqueta real.

    En produccion, este target puede reemplazarse por una columna historica como
    conversion_visita, pago_exitoso o visita_prioritaria.
    """
    estadistico = feature_store["score_estadistico"].astype(float)
    completados = feature_store["tasa_completados"].astype(float)
    valor = np.log1p(feature_store["monto_total"].astype(float))
    valor = valor / valor.max() if valor.max() > 0 else valor
    target = (0.62 * estadistico) + (0.23 * completados) + (0.15 * valor)
    return target.clip(0, 1)


def entrenar_mlp(
    feature_store: pd.DataFrame,
    model_path: str | Path = MODEL_PATH,
) -> Tuple[Pipeline, pd.DataFrame, dict]:
    """Entrena un MLPRegressor y devuelve predicciones de prioridad."""
    datos = feature_store.copy()
    datos["target_prioridad"] = (
        datos["target_prioridad"].astype(float)
        if "target_prioridad" in datos.columns
        else _crear_target_prioridad(datos)
    )

    categorical_presentes = [col for col in CATEGORICAL_FEATURES if col in datos.columns]
    preprocesador = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", MinMaxScaler()),
                    ]
                ),
                NUMERIC_FEATURES,
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_presentes,
            ),
        ],
        remainder="drop",
    )

    modelo = MLPRegressor(
        hidden_layer_sizes=(32, 16),
        activation="relu",
        solver="adam",
        alpha=0.001,
        learning_rate_init=0.01,
        max_iter=1200,
        random_state=42,
    )

    pipeline = Pipeline(steps=[("preprocesador", preprocesador), ("modelo", modelo)])
    x = datos[NUMERIC_FEATURES + categorical_presentes]
    y = datos["target_prioridad"]
    pipeline.fit(x, y)

    predicciones = pipeline.predict(x)
    datos["probabilidad_prioridad_visita"] = np.clip(predicciones, 0, 1)
    datos = datos.sort_values("probabilidad_prioridad_visita", ascending=False).reset_index(drop=True)

    metricas = {
        "mae_entrenamiento": float(mean_absolute_error(y, predicciones)),
        "r2_entrenamiento": float(r2_score(y, predicciones)) if len(datos) > 1 else 1.0,
        "clientes_entrenados": int(len(datos)),
    }

    ruta_modelo = Path(model_path)
    ruta_modelo.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, ruta_modelo)

    return pipeline, datos, metricas


def cargar_modelo(model_path: str | Path = MODEL_PATH) -> Pipeline:
    """Carga el MLP entrenado desde disco."""
    ruta = Path(model_path)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el modelo entrenado: {ruta}")
    return joblib.load(ruta)


def predecir_prioridad(modelo: Pipeline, feature_store: pd.DataFrame) -> pd.DataFrame:
    """Agrega la probabilidad de prioridad de visita a un Feature Store."""
    datos = feature_store.copy()
    categorical_presentes = [col for col in CATEGORICAL_FEATURES if col in datos.columns]
    x = datos[NUMERIC_FEATURES + categorical_presentes]
    datos["probabilidad_prioridad_visita"] = np.clip(modelo.predict(x), 0, 1)
    return datos.sort_values("probabilidad_prioridad_visita", ascending=False).reset_index(drop=True)
