import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
from sqlalchemy import text
from pathlib import Path
from scipy.spatial import cKDTree

from app.core.database import engine

MODEL_DIR = Path("app/ml/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

async def fetch_and_prepare_data():
    """Descarga los datos agregados desde la BD y construye el panel de ML"""
    async with engine.begin() as conn:
        # 1. Traer puntos de presion y sus coordenadas para asignar reclamos
        puntos_df = await conn.run_sync(lambda sync_conn: pd.read_sql(
            "SELECT codigo_punto, latitud, longitud FROM puntos_presion WHERE latitud IS NOT NULL", sync_conn
        ))
        
        # 2. Reclamos Historicos (fugas)
        reclamos_df = await conn.run_sync(lambda sync_conn: pd.read_sql(
            "SELECT fecha_registro, latitud, longitud FROM reclamos_historicos WHERE latitud IS NOT NULL", sync_conn
        ))
        
        # 3. Registros de Presion (features)
        # Hacemos la agregacion mensual en la BD
        presion_query = """
            SELECT 
                pp.codigo_punto as pressure_point,
                CAST(EXTRACT(YEAR FROM rp.fecha_hora) AS INTEGER) as year,
                CAST(EXTRACT(MONTH FROM rp.fecha_hora) AS INTEGER) as month,
                AVG(rp.presion_mca) as pressure_mean,
                COALESCE(STDDEV(rp.presion_mca), 0) as pressure_std,
                MIN(rp.presion_mca) as pressure_min,
                MAX(rp.presion_mca) as pressure_max,
                MAX(rp.presion_mca) - MIN(rp.presion_mca) as pressure_range,
                AVG(rp.temperatura_c) as temp_mean,
                MAX(rp.temperatura_c) as temp_max
            FROM registros_presion rp
            JOIN puntos_presion pp ON rp.punto_presion_id = pp.id
            GROUP BY pp.codigo_punto, EXTRACT(YEAR FROM rp.fecha_hora), EXTRACT(MONTH FROM rp.fecha_hora)
        """
        loggers_df = await conn.run_sync(lambda sync_conn: pd.read_sql(text(presion_query), sync_conn))
        
    # Asignar cada reclamo al punto de presion mas cercano usando cKDTree
    if not puntos_df.empty and not reclamos_df.empty:
        tree = cKDTree(puntos_df[['latitud', 'longitud']].values)
        dists, idxs = tree.query(reclamos_df[['latitud', 'longitud']].values)
        reclamos_df['pressure_point'] = puntos_df.iloc[idxs]['codigo_punto'].values
        reclamos_df['year'] = pd.to_datetime(reclamos_df['fecha_registro']).dt.year
        reclamos_df['month'] = pd.to_datetime(reclamos_df['fecha_registro']).dt.month
        
        targets = reclamos_df.groupby(['pressure_point', 'year', 'month']).size().reset_index(name='n_fuga')
    else:
        targets = pd.DataFrame(columns=['pressure_point', 'year', 'month', 'n_fuga'])
        
    # Merge loggers con targets
    loggers_df['origin'] = 'hydra'
    targets['origin'] = 'hydra'
    targets['n_operativos'] = 0 # Dummy por ahora, si tuvieramos operativos podriamos contarlos
    
    panel = loggers_df.merge(targets, on=['origin', 'pressure_point', 'year', 'month'], how='left')
    panel['n_fuga'] = panel['n_fuga'].fillna(0)
    panel['n_operativos'] = panel['n_operativos'].fillna(0)
    
    # Rellenar con 0 para meses donde no hubo reclamos hasta el mes maximo actual
    panel['date'] = pd.to_datetime(panel['year'].astype(str) + '-' + panel['month'].astype(str) + '-01')
    panel = panel.sort_values(['origin', 'pressure_point', 'year', 'month']).reset_index(drop=True)
    
    # Feature Engineering (Mismo que el notebook m_2)
    grp = panel.groupby(['origin', 'pressure_point'])
    
    lag_features = [
        'pressure_mean', 'pressure_std', 'pressure_min', 'pressure_max', 
        'temp_mean', 'temp_max', 'pressure_range',
        'n_fuga', 'n_operativos',
    ]
    
    # Para simplificar y evitar NaN, 'pressure_p10' y 'sudden_drop_rate' se pueden inicializar a 0 si faltan
    panel['pressure_p10'] = panel['pressure_min'] + (panel['pressure_range'] * 0.1)
    panel['sudden_drop_rate'] = 0
    lag_features.extend(['pressure_p10', 'sudden_drop_rate'])
    
    for feat in lag_features:
        panel[f'{feat}_lag1'] = grp[feat].shift(1)
        panel[f'{feat}_roll3'] = grp[feat].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
        # roll3_incl
        panel[f'{feat}_roll3_incl'] = grp[feat].transform(lambda s: s.rolling(3, min_periods=1).mean())

    panel['target_fuga_next'] = grp['n_fuga'].shift(-1)
    panel['risk_fuga_next'] = (panel['target_fuga_next'] > 0).astype(float)
    
    panel['month_sin'] = np.sin(2 * np.pi * panel['month'] / 12)
    panel['month_cos'] = np.cos(2 * np.pi * panel['month'] / 12)
    
    return panel

async def train_model():
    """Entrena el modelo usando los datos de la base de datos (m_3_train_eval)"""
    panel = await fetch_and_prepare_data()
    
    FEATURES = [
        'n_fuga', 'n_fuga_roll3_incl', 'n_operativos', 'n_operativos_roll3_incl',
        'pressure_std', 'pressure_std_roll3_incl', 'pressure_mean', 'pressure_mean_roll3_incl',
        'sudden_drop_rate', 'pressure_min', 'pressure_p10',
        'month_sin', 'month_cos',
    ]
    TARGET = 'risk_fuga_next'
    
    data = panel.dropna(subset=FEATURES + [TARGET]).sort_values('date').reset_index(drop=True)
    if len(data) < 10:
        return {"success": False, "message": "No hay suficientes datos históricos para entrenar el modelo."}
        
    X = data[FEATURES].values
    y = data[TARGET].values.astype(int)
    
    # Usar Random Forest
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=4, min_samples_leaf=10,
        class_weight='balanced', random_state=42
    )
    
    # Entrenar modelo final con todos los datos
    rf.fit(X, y)
    
    # Guardar scaler y modelo
    scaler = StandardScaler()
    scaler.fit(X)
    
    artifacts = {
        'model': rf,
        'scaler': scaler,
        'features': FEATURES,
        'trained_at': datetime.now().isoformat(),
        'n_samples': len(data)
    }
    
    model_path = MODEL_DIR / 'rf_model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(artifacts, f)
        
    return {"success": True, "message": f"Modelo entrenado exitosamente con {len(data)} muestras.", "path": str(model_path)}

def predict_risk(month_data: pd.DataFrame) -> dict:
    """Predice el riesgo de fugas basándose en el modelo entrenado."""
    model_path = MODEL_DIR / 'rf_model.pkl'
    if not model_path.exists():
        return {"error": "El modelo no ha sido entrenado aún."}
        
    with open(model_path, 'rb') as f:
        artifacts = pickle.load(f)
        
    model = artifacts['model']
    features = artifacts['features']
    
    if not all(f in month_data.columns for f in features):
        return {"error": "Los datos proporcionados no contienen todas las features requeridas."}
        
    X = month_data[features].values
    proba = model.predict_proba(X)[:, 1]
    
    results = []
    for i, row in month_data.iterrows():
        results.append({
            "pressure_point": row.get('pressure_point', 'Desconocido'),
            "risk_probability": round(float(proba[i]), 3),
            "risk_level": "ALTO" if proba[i] > 0.6 else ("MEDIO" if proba[i] > 0.3 else "BAJO")
        })
        
    return {"predictions": results}
