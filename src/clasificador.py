"""
clasificador.py — Clasificación automática de nuevas quejas con NLP
Usa TF-IDF + Logistic Regression para categorizar descripciones
"""
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report
import pickle
import re


# ─── Preprocesamiento ────────────────────────────────────────────────────────

def limpiar_texto(texto: str) -> str:
    texto = str(texto).upper()
    texto = re.sub(r'\d+', '', texto)          # Eliminar números
    texto = re.sub(r'[^\w\s]', ' ', texto)     # Eliminar puntuación
    texto = re.sub(r'\s+', ' ', texto).strip() # Normalizar espacios
    return texto


# ─── Etiquetado (reglas de negocio) ─────────────────────────────────────────

def etiquetar(texto: str) -> str:
    t = str(texto).upper()
    if ("PAGO" in t or "COBRO" in t or "MORA" in t or "SALARIO" in t) and "INCAPACIDAD" in t:
        return "DEMORA_PAGO_INCAPACIDAD"
    if "INCAPACIDAD" in t and any(w in t for w in ["ESTADO", "INFORMACIÓN", "INFORMACION", "SABER", "CONSULTA"]):
        return "CONSULTA_ESTADO_INCAPACIDAD"
    if "RADICADO" in t and "INCAPACIDAD" in t:
        return "SEGUIMIENTO_RADICADO"
    if "CERTIFICADO" in t:
        return "SOLICITUD_CERTIFICADO"
    if "ACCIDENTE" in t and "TRABAJO" in t:
        return "ACCIDENTE_TRABAJO"
    if "INCAPACIDAD" in t:
        return "GESTION_INCAPACIDAD"
    return "OTRA_SOLICITUD"


# ─── Entrenamiento ───────────────────────────────────────────────────────────

def entrenar_modelo(df: pd.DataFrame):
    """
    Entrena un clasificador TF-IDF + Logistic Regression.
    Retorna (vectorizer, modelo, reporte).
    """
    df = df.copy()
    df["texto_limpio"] = df["Descripción"].apply(limpiar_texto)
    df["etiqueta"] = df["Descripción"].apply(etiquetar)

    X = df["texto_limpio"]
    y = df["etiqueta"]

    # Eliminar clases con muy pocos ejemplos para CV estable
    conteo = y.value_counts()
    clases_validas = conteo[conteo >= 5].index
    mask = y.isin(clases_validas)
    X, y = X[mask], y[mask]

    vectorizer = TfidfVectorizer(
        max_features=3000,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True
    )
    X_vec = vectorizer.fit_transform(X)

    modelo = LogisticRegression(max_iter=500, C=1.0, class_weight="balanced")

    # Validación cruzada
    scores = cross_val_score(modelo, X_vec, y, cv=5, scoring="f1_macro")
    print(f"F1-Macro (CV-5): {scores.mean():.3f} ± {scores.std():.3f}")

    # Entrenamiento final
    X_train, X_test, y_train, y_test = train_test_split(X_vec, y, test_size=0.2, random_state=42, stratify=y)
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)
    reporte = classification_report(y_test, y_pred)
    print("\nReporte de clasificación (test set):\n", reporte)

    return vectorizer, modelo, reporte


# ─── Persistencia ────────────────────────────────────────────────────────────

def guardar_modelo(vectorizer, modelo, path_prefix: str = "../outputs/modelo"):
    with open(f"{path_prefix}_vectorizer.pkl", "wb") as f:
        pickle.dump(vectorizer, f)
    with open(f"{path_prefix}_lr.pkl", "wb") as f:
        pickle.dump(modelo, f)
    print(f"✅ Modelo guardado en {path_prefix}_*.pkl")


def cargar_modelo(path_prefix: str = "../outputs/modelo"):
    with open(f"{path_prefix}_vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(f"{path_prefix}_lr.pkl", "rb") as f:
        modelo = pickle.load(f)
    return vectorizer, modelo


# ─── Predicción sobre nuevos datos ───────────────────────────────────────────

def clasificar_nuevas_quejas(df_nuevo: pd.DataFrame, vectorizer, modelo) -> pd.DataFrame:
    """
    Clasifica automáticamente un DataFrame con nuevas quejas.
    Agrega columna 'Categoria_Predicha' y 'Probabilidad_Max'.
    """
    df_nuevo = df_nuevo.copy()
    textos = df_nuevo["Descripción"].apply(limpiar_texto)
    X_vec = vectorizer.transform(textos)
    df_nuevo["Categoria_Predicha"] = modelo.predict(X_vec)
    probs = modelo.predict_proba(X_vec)
    df_nuevo["Probabilidad_Max"] = probs.max(axis=1).round(3)
    return df_nuevo


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = pd.read_excel("../data/BD_Quejas_Analitica.xlsx")
    print(f"Registros cargados: {len(df)}")

    vectorizer, modelo, reporte = entrenar_modelo(df)
    guardar_modelo(vectorizer, modelo)

    # Demo: clasificar primeras 5 filas
    muestra = df.head(5)
    resultado = clasificar_nuevas_quejas(muestra, vectorizer, modelo)
    print("\nMuestra clasificada:")
    print(resultado[["Nombre del cliente", "Categoria_Predicha", "Probabilidad_Max"]].to_string())
