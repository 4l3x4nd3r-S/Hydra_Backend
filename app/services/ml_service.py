import os
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
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
        def _run_query(sync_conn, q):
            res = sync_conn.execute(text(q))
            return pd.DataFrame(res.fetchall(), columns=res.keys())

        # 1. Traer puntos de presion y sus coordenadas para asignar reclamos
        puntos_df = await conn.run_sync(lambda c: _run_query(c, 
            "SELECT id as punto_id, origen, codigo_punto, latitud, longitud FROM puntos_presion WHERE latitud IS NOT NULL"
        ))
        
        # 2. Reclamos Historicos (fugas y operativos)
        reclamos_df = await conn.run_sync(lambda c: _run_query(c, 
            "SELECT fecha_registro, latitud, longitud, tipo_problema FROM reclamos_historicos WHERE latitud IS NOT NULL"
        ))
        
        # 3. Registros de Presion (features)
        # Hacemos la agregacion mensual en la BD
        presion_query = """
            WITH diffs AS (
                SELECT 
                    pp.origen as origin,
                    pp.codigo_punto as pressure_point,
                    EXTRACT(YEAR FROM rp.fecha_hora) as year,
                    EXTRACT(MONTH FROM rp.fecha_hora) as month,
                    rp.presion_mca,
                    rp.temperatura_c,
                    rp.presion_mca - LAG(rp.presion_mca) OVER (PARTITION BY pp.codigo_punto ORDER BY rp.fecha_hora) as pressure_diff
                FROM registros_presion rp
                JOIN puntos_presion pp ON rp.punto_presion_id = pp.id
            ),
            thresholds AS (
                SELECT PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY pressure_diff) as drop_threshold
                FROM diffs
            )
            SELECT 
                d.origin,
                d.pressure_point,
                CAST(d.year AS INTEGER) as year,
                CAST(d.month AS INTEGER) as month,
                AVG(d.presion_mca) as pressure_mean,
                COALESCE(STDDEV(d.presion_mca), 0) as pressure_std,
                MIN(d.presion_mca) as pressure_min,
                MAX(d.presion_mca) as pressure_max,
                MAX(d.presion_mca) - MIN(d.presion_mca) as pressure_range,
                PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY d.presion_mca) as pressure_p10,
                AVG(d.temperatura_c) as temp_mean,
                MAX(d.temperatura_c) as temp_max,
                SUM(CASE WHEN d.pressure_diff < t.drop_threshold THEN 1 ELSE 0 END) as n_sudden_drops,
                COUNT(*) as n_readings,
                CAST(SUM(CASE WHEN d.pressure_diff < t.drop_threshold THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as sudden_drop_rate
            FROM diffs d
            CROSS JOIN thresholds t
            GROUP BY d.origin, d.pressure_point, d.year, d.month
        """
        loggers_df = await conn.run_sync(lambda c: _run_query(c, presion_query))
        
    # Asignar cada reclamo al punto de presion mas cercano usando cKDTree
    if not puntos_df.empty and not reclamos_df.empty:
        tree = cKDTree(puntos_df[['latitud', 'longitud']].values)
        dists, idxs = tree.query(reclamos_df[['latitud', 'longitud']].values)
        reclamos_df['pressure_point'] = puntos_df.iloc[idxs]['codigo_punto'].values
        reclamos_df['origin'] = puntos_df.iloc[idxs]['origen'].values
        reclamos_df['year'] = pd.to_datetime(reclamos_df['fecha_registro']).dt.year
        reclamos_df['month'] = pd.to_datetime(reclamos_df['fecha_registro']).dt.month
        
        # Filtros de tipos de problemas dinámicos
        reclamos_df['tipo_problema'] = reclamos_df['tipo_problema'].fillna('').str.upper()
        
        # Consideramos evento crítico (fuga/problema de red) a cualquier OP-X, o los B históricos de fuga, o si dice FUGA
        cond_op = reclamos_df['tipo_problema'].str.contains(r'^OP', regex=True)
        cond_b = reclamos_df['tipo_problema'].str.contains(r'^(B10|B5|B1)\b', regex=True)
        cond_fuga = reclamos_df['tipo_problema'].str.contains('FUGA', regex=False)
        
        reclamos_df['is_fuga'] = cond_op | cond_b | cond_fuga
        
        # El resto lo consideramos trabajos operativos/administrativos menores
        reclamos_df['is_operational'] = ~reclamos_df['is_fuga']
        
        reclamos_fuga = reclamos_df[reclamos_df['is_fuga']]
        reclamos_op = reclamos_df[reclamos_df['is_operational']]
        
        t_fuga = reclamos_fuga.groupby(['origin', 'pressure_point', 'year', 'month']).size().reset_index(name='n_fuga')
        t_op = reclamos_op.groupby(['origin', 'pressure_point', 'year', 'month']).size().reset_index(name='n_operativos')
        
        targets = t_fuga.merge(t_op, on=['origin', 'pressure_point', 'year', 'month'], how='outer')
        targets['n_fuga'] = targets['n_fuga'].fillna(0)
        targets['n_operativos'] = targets['n_operativos'].fillna(0)
    else:
        targets = pd.DataFrame(columns=['origin', 'pressure_point', 'year', 'month', 'n_fuga', 'n_operativos'])
        
    # Merge loggers con targets
    panel = loggers_df.merge(targets, on=['origin', 'pressure_point', 'year', 'month'], how='left')
    
    if not targets.empty:
        reclamos_max_year = targets['year'].max()
        reclamos_max_month = targets[targets['year'] == reclamos_max_year]['month'].max()
        reclamos_max_date = pd.to_datetime(f"{int(reclamos_max_year)}-{int(reclamos_max_month)}-01")
    else:
        reclamos_max_date = pd.to_datetime('today')
        
    panel['date'] = pd.to_datetime(panel['year'].astype(str) + '-' + panel['month'].astype(str) + '-01')
    within_range = panel['date'] <= reclamos_max_date
    
    for col in ['n_fuga', 'n_operativos']:
        if col in panel.columns:
            panel.loc[within_range, col] = panel.loc[within_range, col].fillna(0)
            
    panel = panel.sort_values(['origin', 'pressure_point', 'year', 'month']).reset_index(drop=True)
    
    # Feature Engineering (Exactamente como m_2)
    grp = panel.groupby(['origin', 'pressure_point'])
    
    lag_features = [
        'pressure_mean', 'pressure_std', 'pressure_min', 'pressure_max', 'pressure_p10',
        'temp_mean', 'temp_max', 'sudden_drop_rate', 'pressure_range',
        'n_fuga', 'n_operativos',
    ]
    
    for feat in lag_features:
        if feat in panel.columns:
            panel[f'{feat}_lag1'] = grp[feat].shift(1)
            panel[f'{feat}_roll3'] = grp[feat].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
            panel[f'{feat}_roll3_incl'] = grp[feat].transform(lambda s: s.rolling(3, min_periods=1).mean())

    panel['prev_date'] = grp['date'].shift(1)
    panel['months_since_last_visit'] = (
        (panel['date'].dt.year - panel['prev_date'].dt.year) * 12 +
        (panel['date'].dt.month - panel['prev_date'].dt.month)
    )

    if 'pressure_mean_lag1' in panel.columns:
        panel['pressure_mean_delta'] = panel['pressure_mean'] - panel['pressure_mean_lag1']
        
    panel['month_sin'] = np.sin(2 * np.pi * panel['month'] / 12)
    panel['month_cos'] = np.cos(2 * np.pi * panel['month'] / 12)
    
    panel['target_fuga_next'] = grp['n_fuga'].shift(-1)
    panel['target_operativos_next'] = grp['n_operativos'].shift(-1)
    panel['next_date'] = grp['date'].shift(-1)
    panel['months_to_next_visit'] = (
        (panel['next_date'].dt.year - panel['date'].dt.year) * 12 +
        (panel['next_date'].dt.month - panel['date'].dt.month)
    )
    
    panel['risk_fuga_next'] = (panel['target_fuga_next'] > 0).astype(float)
    panel.loc[panel['target_fuga_next'].isna(), 'risk_fuga_next'] = np.nan
    
    panel['risk_operativos_next'] = (panel['target_operativos_next'] > 0).astype(float)
    panel.loc[panel['target_operativos_next'].isna(), 'risk_operativos_next'] = np.nan
    
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
    
    # 1. Evaluacion con TimeSeriesSplit (exactamente como m_3)
    N_SPLITS = 5
    # Si hay pocos datos, ajustamos N_SPLITS
    actual_splits = min(N_SPLITS, len(data) // 10)
    
    metrics_history = []
    if actual_splits > 1:
        tscv = TimeSeriesSplit(n_splits=actual_splits)
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
                continue
                
            rf_cv = RandomForestClassifier(
                n_estimators=300, max_depth=4, min_samples_leaf=10,
                class_weight='balanced', random_state=42
            )
            rf_cv.fit(X_train, y_train)
            pred_rf = rf_cv.predict(X_test)
            proba_rf = rf_cv.predict_proba(X_test)[:, 1]
            
            metrics_history.append({
                'precision': precision_score(y_test, pred_rf, zero_division=0),
                'recall': recall_score(y_test, pred_rf, zero_division=0),
                'f1': f1_score(y_test, pred_rf, zero_division=0),
                'auc': roc_auc_score(y_test, proba_rf),
            })
            
    # Promediar metricas
    final_metrics = {"precision": 0, "recall": 0, "f1": 0, "auc": 0}
    if metrics_history:
        df_metrics = pd.DataFrame(metrics_history)
        final_metrics = {
            "precision": float(round(df_metrics['precision'].mean(), 3)),
            "recall": float(round(df_metrics['recall'].mean(), 3)),
            "f1": float(round(df_metrics['f1'].mean(), 3)),
            "auc": float(round(df_metrics['auc'].mean(), 3))
        }
    
    # 2. Entrenar modelo final para produccion con TODOS los datos
    rf = RandomForestClassifier(
        n_estimators=300, max_depth=4, min_samples_leaf=10,
        class_weight='balanced', random_state=42
    )
    rf.fit(X, y)
    
    artifacts = {
        'model': rf,
        'features': FEATURES,
        'trained_at': datetime.now().isoformat(),
        'n_samples': len(data),
        'metrics': final_metrics
    }
    
    model_path = MODEL_DIR / 'rf_model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(artifacts, f)
        
    return {
        "success": True, 
        "message": f"Modelo entrenado exitosamente con {len(data)} muestras.",
        "metrics": final_metrics,
        "path": str(model_path)
    }

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
        
    month_data = month_data.reset_index(drop=True)
    X = month_data[features].fillna(0).values
    
    proba = model.predict_proba(X)[:, 1]
    
    # Lógica de umbrales fijos sobre el risk_score absoluto (Sin Percentiles)
    results = []
    for i, row in month_data.iterrows():
        prob = float(proba[i])
        
        # Asignar nivel basado en el risk_score
        if prob >= 0.60:
            risk = "ALTO"
        elif prob >= 0.40:
            risk = "MEDIO"
        else:
            risk = "BAJO"
            
        results.append({
            "origen": row.get('origin', 'Desconocido'),
            "pressure_point": row.get('pressure_point', 'Desconocido'),
            "risk_probability": round(prob, 3),
            "risk_level": risk
        })
        
    return {"predictions": results}
