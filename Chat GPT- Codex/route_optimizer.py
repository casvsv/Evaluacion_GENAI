"""
Optimizacion de rutas con Google OR-Tools.
"""

from __future__ import annotations

import json
from math import asin, cos, radians, sin, sqrt
from typing import Dict, List

import numpy as np
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def _registros_json(dataframe: pd.DataFrame) -> List[Dict]:
    """Convierte tipos de Pandas/NumPy a valores compatibles con una API JSON."""
    return json.loads(dataframe.to_json(orient="records", date_format="iso"))


def distancia_haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia aproximada en kilometros entre dos coordenadas."""
    radio_tierra_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radio_tierra_km * asin(sqrt(a))


def crear_matriz_costos(clientes: pd.DataFrame, peso_prioridad: float = 0.35) -> List[List[int]]:
    """
    Crea una matriz de costos enteros.

    El costo de ir hacia un cliente baja si su probabilidad de prioridad es alta.
    """
    coords = clientes[["latitud", "longitud"]].to_numpy(dtype=float)
    prioridades = clientes["probabilidad_prioridad_visita"].fillna(0).clip(0, 1).to_numpy(dtype=float)
    n = len(clientes)
    matriz = np.zeros((n, n), dtype=int)

    for i in range(n):
        for j in range(n):
            if i == j:
                matriz[i, j] = 0
                continue
            distancia = distancia_haversine_km(coords[i][0], coords[i][1], coords[j][0], coords[j][1])
            factor_prioridad = 1 - (peso_prioridad * prioridades[j])
            matriz[i, j] = max(1, int(distancia * factor_prioridad * 1000))

    return matriz.tolist()


def optimizar_ruta(
    clientes: pd.DataFrame,
    lat_inicio: float | None = None,
    lon_inicio: float | None = None,
    peso_prioridad: float = 0.35,
) -> Dict:
    """Resuelve un TSP priorizado y devuelve la secuencia optima de visita."""
    if clientes.empty:
        raise ValueError("No hay clientes para optimizar.")

    requeridas = {"cliente_id", "cliente_nombre", "latitud", "longitud", "probabilidad_prioridad_visita"}
    faltantes = requeridas.difference(clientes.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas requeridas para optimizar: {sorted(faltantes)}")

    clientes_ruta = clientes.copy().reset_index(drop=True)

    if lat_inicio is not None and lon_inicio is not None:
        origen = pd.DataFrame(
            [
                {
                    "cliente_id": "ORIGEN",
                    "cliente_nombre": "Punto de inicio",
                    "zona": "Base",
                    "latitud": lat_inicio,
                    "longitud": lon_inicio,
                    "probabilidad_prioridad_visita": 0.0,
                }
            ]
        )
    else:
        origen = pd.DataFrame(
            [
                {
                    "cliente_id": "ORIGEN",
                    "cliente_nombre": "Centroide de zona",
                    "zona": "Base",
                    "latitud": clientes_ruta["latitud"].mean(),
                    "longitud": clientes_ruta["longitud"].mean(),
                    "probabilidad_prioridad_visita": 0.0,
                }
            ]
        )

    nodos = pd.concat([origen, clientes_ruta], ignore_index=True)
    matriz_costos = crear_matriz_costos(nodos, peso_prioridad=peso_prioridad)

    manager = pywrapcp.RoutingIndexManager(len(matriz_costos), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def costo_callback(from_index: int, to_index: int) -> int:
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return matriz_costos[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(costo_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    parametros = pywrapcp.DefaultRoutingSearchParameters()
    parametros.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    parametros.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    parametros.time_limit.FromSeconds(5)

    solucion = routing.SolveWithParameters(parametros)
    if solucion is None:
        raise RuntimeError("OR-Tools no encontro una solucion para la ruta.")

    index = routing.Start(0)
    orden_nodos = []
    costo_total = 0

    while not routing.IsEnd(index):
        nodo = manager.IndexToNode(index)
        orden_nodos.append(nodo)
        anterior = index
        index = solucion.Value(routing.NextVar(index))
        costo_total += routing.GetArcCostForVehicle(anterior, index, 0)

    secuencia = nodos.iloc[orden_nodos].copy()
    secuencia["orden_visita"] = range(len(secuencia))
    secuencia_clientes = secuencia[secuencia["cliente_id"] != "ORIGEN"].copy()
    secuencia_clientes["orden_visita"] = range(1, len(secuencia_clientes) + 1)

    distancia_km = 0.0
    puntos = secuencia[["latitud", "longitud"]].to_numpy(dtype=float)
    for i in range(len(puntos) - 1):
        distancia_km += distancia_haversine_km(puntos[i][0], puntos[i][1], puntos[i + 1][0], puntos[i + 1][1])

    origen_json = _registros_json(origen)[0]
    ruta_json = _registros_json(secuencia_clientes)
    puntos_json = _registros_json(secuencia)

    return {
        "resumen": {
            "total_clientes": int(len(secuencia_clientes)),
            "distancia_aproximada_km": round(float(distancia_km), 2),
            "costo_priorizado": int(costo_total),
            "peso_prioridad": float(peso_prioridad),
        },
        "origen": origen_json,
        "ruta": ruta_json,
        "puntos_mapa": puntos_json,
    }
