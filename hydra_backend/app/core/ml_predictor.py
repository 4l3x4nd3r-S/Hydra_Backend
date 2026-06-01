"""
Motor de inferencia ML para detección de anomalías de presión.
Modelo: HistGradientBoostingClassifier entrenado con datos EMAPAT 2024.
"""
import logging
import os

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Umbral de probabilidad para considerar anomalía (reduce falsos positivos)
ANOMALY_THRESHOLD = 0.60

# Ruta al modelo (.pkl está en la raíz del proyecto, junto al Procfile)
_MODEL_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "emapat_anomaly_model.pkl")
)

# Las 28 features exactas que espera el modelo (mismo orden que el entrenamiento)
FEATURE_COLS = [
    "Pressure", "Temperature",
    "Presion_Lag_5m", "Presion_Lag_10m", "Presion_Lag_15m", "Presion_Lag_30m",
    "Presion_Lag_1h", "Presion_Lag_2h", "Presion_Lag_6h", "Presion_Lag_12h", "Presion_Lag_24h",
    "Gradiente_Presion_5min", "Aceleracion_Presion_5min",
    "Presion_Media_30m", "Presion_Media_1h", "Presion_Media_6h", "Presion_Media_24h",
    "Presion_Std_30m", "Presion_Std_1h", "Presion_Std_6h", "Presion_Std_24h",
    "Presion_RMS_1h", "Presion_Rango_6h",
    "Hora_Seno", "Hora_Coseno", "Es_Fin_De_Semana", "Mes_Del_Anio",
    "Desviacion_Historica_Presion",
]

_model = None


def _get_model():
    global _model
    if _model is None:
        if os.path.exists(_MODEL_PATH):
            _model = joblib.load(_MODEL_PATH)
            logger.info("Modelo ML cargado: %s", _MODEL_PATH)
        else:
            logger.warning("Modelo ML no encontrado en %s", _MODEL_PATH)
    return _model


def _compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula las 28 features a partir del historial de presiones.
    Entrada: DataFrame con columnas timestamp, presion, temperatura
    (ordenado cronológicamente, lecturas cada 5 minutos)
    """
    df = df.sort_values("timestamp").reset_index(drop=True).copy()

    df["Pressure"] = df["presion"].astype(float)
    temp_media = df["temperatura"].dropna().mean() if df["temperatura"].notna().any() else 25.0
    df["Temperature"] = df["temperatura"].fillna(temp_media).astype(float)

    # Lag features (1 período = 5 minutos)
    _lags = {
        "Presion_Lag_5m": 1,  "Presion_Lag_10m": 2, "Presion_Lag_15m": 3,
        "Presion_Lag_30m": 6, "Presion_Lag_1h": 12,  "Presion_Lag_2h": 24,
        "Presion_Lag_6h": 72, "Presion_Lag_12h": 144, "Presion_Lag_24h": 288,
    }
    for col, n in _lags.items():
        df[col] = df["Pressure"].shift(n).bfill()

    # Gradiente (cambio en 5 min) y aceleración (cambio del gradiente)
    df["Gradiente_Presion_5min"] = df["Pressure"].diff(1).fillna(0.0)
    df["Aceleracion_Presion_5min"] = df["Gradiente_Presion_5min"].diff(1).fillna(0.0)

    # Estadísticas móviles
    for suffix, w in [("30m", 6), ("1h", 12), ("6h", 72), ("24h", 288)]:
        roll = df["Pressure"].rolling(w, min_periods=1)
        df[f"Presion_Media_{suffix}"] = roll.mean()
        df[f"Presion_Std_{suffix}"] = roll.std().fillna(0.0)

    df["Presion_RMS_1h"] = (
        (df["Pressure"] ** 2).rolling(12, min_periods=1).mean() ** 0.5
    )
    df["Presion_Rango_6h"] = (
        df["Pressure"].rolling(72, min_periods=1).max()
        - df["Pressure"].rolling(72, min_periods=1).min()
    )

    # Encoding cíclico de la hora
    ts = pd.to_datetime(df["timestamp"])
    hora = ts.dt.hour + ts.dt.minute / 60.0
    df["Hora_Seno"] = np.sin(2 * np.pi * hora / 24)
    df["Hora_Coseno"] = np.cos(2 * np.pi * hora / 24)
    df["Es_Fin_De_Semana"] = ts.dt.dayofweek.isin([5, 6]).astype(int)
    df["Mes_Del_Anio"] = ts.dt.month

    # Desviación respecto a la media histórica del sensor
    df["Desviacion_Historica_Presion"] = (df["Pressure"] - df["Pressure"].mean()).abs()

    return df


def detectar_anomalias(historial: list[dict], n_nuevas: int) -> list[dict]:
    """
    Detecta anomalías en las últimas n_nuevas lecturas usando el historial completo
    del sensor como contexto para calcular lags y estadísticas.

    Args:
        historial: Lista de dicts con {timestamp, presion, temperatura}.
                   Debe incluir lecturas previas + las n_nuevas al final,
                   ordenadas cronológicamente.
        n_nuevas:  Cantidad de lecturas recién cargadas (las últimas del historial).

    Returns:
        Lista de anomalías: [{timestamp, presion_mca, probabilidad, nivel}]
    """
    model = _get_model()
    if model is None or not historial or n_nuevas <= 0:
        return []

    try:
        df = pd.DataFrame(historial)
        df = _compute_features(df)

        nuevas = df.tail(n_nuevas).copy()
        X = nuevas[FEATURE_COLS].values

        probas = model.predict_proba(X)[:, 1]
    except Exception as exc:
        logger.error("Error en inferencia ML: %s", exc)
        return []

    anomalias = []
    for i, (_, row) in enumerate(nuevas.iterrows()):
        p = float(probas[i])
        if p >= ANOMALY_THRESHOLD:
            nivel = "CRITICA" if p >= 0.85 else ("ALTA" if p >= 0.75 else "MEDIA")
            anomalias.append({
                "timestamp": row["timestamp"],
                "presion_mca": round(float(row["Pressure"]), 3),
                "probabilidad": round(p, 4),
                "nivel": nivel,
            })

    return anomalias
