"""
predictor_insatisfaccion.py — Modelo predictivo de clientes con alta insatisfacción
Responde: ¿Desde los datos se pueden predecir clientes con alta probabilidad de insatisfacción?
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings("ignore")


def construir_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering a nivel de cliente.
    La variable objetivo es: cliente con >= 3 quejas (alto riesgo).
    """
    from metricas import classify_queja  # reutiliza clasificador de reglas

    df = df.copy()
    df["Categoria"] = df["Descripción"].apply(classify_queja)

    # Agrupar por cliente
    feat = df.groupby("Nombre del cliente").agg(
        total_quejas=("Descripción", "count"),
        canales_distintos=("Canal de comunicación", "nunique"),
        meses_distintos=("Mes apertura del caso", "nunique"),
        tiene_pago=("Categoria", lambda x: int("DEMORA_PAGO_INCAPACIDAD" in x.values)),
        tiene_consulta=("Categoria", lambda x: int("CONSULTA_ESTADO_INCAPACIDAD" in x.values)),
        tiene_accidente=("Categoria", lambda x: int("ACCIDENTE_TRABAJO" in x.values)),
        canal_principal=("Canal de comunicación", lambda x: x.value_counts().index[0]),
    ).reset_index()

    # Codificar canal principal
    le = LabelEncoder()
    feat["canal_enc"] = le.fit_transform(feat["canal_principal"])

    # Variable objetivo: alto riesgo = 3+ quejas
    UMBRAL = 3
    feat["alto_riesgo"] = (feat["total_quejas"] >= UMBRAL).astype(int)

    return feat, le


def entrenar_predictor(feat: pd.DataFrame):
    """Entrena Random Forest para predecir alto riesgo de insatisfacción."""
    feature_cols = [
        "total_quejas", "canales_distintos", "meses_distintos",
        "tiene_pago", "tiene_consulta", "tiene_accidente", "canal_enc"
    ]
    X = feat[feature_cols]
    y = feat["alto_riesgo"]

    modelo = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        class_weight="balanced",
        random_state=42
    )

    scores = cross_val_score(modelo, X, y, cv=5, scoring="roc_auc")
    print(f"AUC-ROC (CV-5): {scores.mean():.3f} ± {scores.std():.3f}")

    modelo.fit(X, y)

    # Importancia de variables
    importancias = pd.Series(modelo.feature_importances_, index=feature_cols)
    print("\nImportancia de variables:")
    print(importancias.sort_values(ascending=False).to_string())

    return modelo, feature_cols


def predecir_riesgo(feat: pd.DataFrame, modelo, feature_cols: list) -> pd.DataFrame:
    """Retorna clientes ordenados por probabilidad de insatisfacción."""
    X = feat[feature_cols]
    feat = feat.copy()
    feat["prob_insatisfaccion"] = modelo.predict_proba(X)[:, 1]
    feat["nivel_riesgo"] = pd.cut(
        feat["prob_insatisfaccion"],
        bins=[0, 0.3, 0.6, 1.0],
        labels=["BAJO", "MEDIO", "ALTO"]
    )
    return feat[["Nombre del cliente", "total_quejas", "prob_insatisfaccion", "nivel_riesgo"]]\
        .sort_values("prob_insatisfaccion", ascending=False)


if __name__ == "__main__":
    df = pd.read_excel(r"./data/BD_Quejas_Analitica.xlsx")
    df["Mes apertura del caso"] = df["Mes apertura del caso"].astype(str)

    print("🔧 Construyendo features...")
    feat, le = construir_features(df)
    print(f"Clientes únicos: {len(feat)}")
    print(f"Clientes alto riesgo (>=3 quejas): {feat['alto_riesgo'].sum()}")

    print("\n🤖 Entrenando modelo...")
    modelo, feature_cols = entrenar_predictor(feat)

    print("\n🎯 Top 15 clientes con mayor riesgo de insatisfacción:")
    ranking = predecir_riesgo(feat, modelo, feature_cols)
    print(ranking.head(15).to_string(index=False))

    # Exportar
    ranking.to_excel(r"./outputs/ranking_riesgo_clientes.xlsx", index=False)
    print("\n✅ Ranking exportado a outputs/ranking_riesgo_clientes.xlsx")
