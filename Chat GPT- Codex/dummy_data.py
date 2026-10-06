"""
Generador de datos historicos falsos para probar el rutero.

Uso:
    python dummy_data.py

Salida:
    data/clientes_historicos_ecuador.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "clientes_historicos_ecuador.csv"
RANDOM_SEED = 42

# Punto de referencia aproximado: Quito, Ecuador.
QUITO_LAT = -0.2298
QUITO_LON = -78.5249


def generar_datos_dummy(total_transacciones: int = 50) -> pd.DataFrame:
    """Crea transacciones historicas con clientes y coordenadas cercanas a Quito."""
    rng = np.random.default_rng(RANDOM_SEED)

    clientes = [
        {
            "cliente_id": f"C{i:03d}",
            "cliente_nombre": f"Cliente Ejecutivo {i:02d}",
            "zona": rng.choice(["Norte", "Centro", "Sur", "Valle"]),
            "latitud": QUITO_LAT + rng.normal(0, 0.035),
            "longitud": QUITO_LON + rng.normal(0, 0.035),
        }
        for i in range(1, 21)
    ]

    fechas = pd.date_range("2026-01-01", "2026-04-30", freq="D")
    registros = []

    for transaccion_id in range(1, total_transacciones + 1):
        cliente = rng.choice(clientes)
        fecha = rng.choice(fechas)

        registros.append(
            {
                "transaccion_id": f"T{transaccion_id:04d}",
                "fecha": pd.Timestamp(fecha).strftime("%Y-%m-%d"),
                "cliente_id": cliente["cliente_id"],
                "cliente_nombre": cliente["cliente_nombre"],
                "zona": cliente["zona"],
                "latitud": round(float(cliente["latitud"]), 6),
                "longitud": round(float(cliente["longitud"]), 6),
                "monto": round(float(rng.uniform(80, 1800)), 2),
                "tipo_transaccion": rng.choice(["cobro", "pedido"], p=[0.55, 0.45]),
                "estado": rng.choice(["completado", "pendiente"], p=[0.82, 0.18]),
            }
        )

    df = pd.DataFrame(registros).sort_values(["fecha", "cliente_id"]).reset_index(drop=True)
    return df


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    df = generar_datos_dummy()
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"Archivo generado: {OUTPUT_FILE.resolve()}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
