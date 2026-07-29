from fastapi import APIRouter, BackgroundTasks, Depends
import pandas as pd
from typing import Dict, Any

from app.services.ml_service import train_model, predict_risk, fetch_and_prepare_data

router = APIRouter(prefix="/ml", tags=["Machine Learning"])

@router.post("/train")
async def trigger_training(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Desencadena el entrenamiento del modelo de predicción de fugas.
    Esto se ejecuta de forma síncrona/asíncrona. Si el panel es grande, debería 
    ejecutarse en background, pero por simplicidad retornamos el estado directo aquí.
    """
    # En producción real con mucha data, usar background_tasks.add_task(train_model)
    # y retornar "Entrenamiento iniciado".
    result = await train_model()
    return result

@router.get("/predict")
async def get_predictions() -> Dict[str, Any]:
    """
    Devuelve las predicciones de riesgo de fuga para el próximo mes 
    basándose en el último mes de datos registrados.
    """
    # 1. Obtener el dataset actual
    panel = await fetch_and_prepare_data()
    if panel.empty:
        return {"error": "No hay datos para realizar predicciones."}
        
    # 2. Filtrar solo el último mes de cada punto de presión
    panel['date'] = pd.to_datetime(panel['date'])
    latest_month = panel['date'].max()
    current_data = panel[panel['date'] == latest_month]
    
    # 3. Predecir
    predictions = predict_risk(current_data)
    
    return {
        "prediction_target_month": (latest_month + pd.DateOffset(months=1)).strftime('%Y-%m'),
        "data_used_month": latest_month.strftime('%Y-%m'),
        "results": predictions
    }
