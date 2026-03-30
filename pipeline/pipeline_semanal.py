"""
pipeline_semanal.py — Flujo automatizado de actualización semanal
Punto d de la prueba técnica

Pasos:
  1. Cargar nuevos datos de quejas (desde ruta o API)
  2. Limpiar y validar
  3. Clasificar automáticamente con el modelo entrenado
  4. Actualizar métricas y reportes
  5. Regenerar dashboard
  6. Notificar (log / email)

Herramientas alternativas:
  - Apache Airflow (producción)
  - GitHub Actions (CI/CD ligero)
  - AWS Lambda + S3 (serverless)
"""

import pandas as pd
import os
import logging
import pickle
import re
from datetime import datetime
from pathlib import Path

# ─── Configuración ────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
MODEL_PREFIX = str(OUTPUT_DIR / "modelo")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "pipeline.log")
    ]
)
log = logging.getLogger(__name__)


# ─── Paso 1: Carga de datos ───────────────────────────────────────────────────

def cargar_nuevos_datos(ruta: str = None) -> pd.DataFrame:
    """
    Carga nuevas quejas desde archivo Excel o simulación.
    En producción: conectar a API / base de datos / SFTP.
    """
    if ruta and os.path.exists(ruta):
        log.info(f"Cargando datos desde: {ruta}")
        return pd.read_excel(ruta)

    # Simulación: tomar últimas N filas de la BD histórica
    log.info("Simulando carga de nuevos datos (últimas 50 filas)...")
    df_hist = pd.read_excel(DATA_DIR / "BD_Quejas_Analitica.xlsx")
    return df_hist.tail(50).copy()


# ─── Paso 2: Validación ───────────────────────────────────────────────────────

COLUMNAS_REQUERIDAS = [
    "Mes apertura del caso",
    "Descripción",
    "Tipo",
    "Nombre del cliente",
    "Canal de comunicación"
]

def validar_datos(df: pd.DataFrame) -> pd.DataFrame:
    log.info("Validando datos...")
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes: {faltantes}")

    nulos_antes = df.isnull().sum().sum()
    df = df.dropna(subset=["Descripción", "Nombre del cliente"])
    df["Descripción"] = df["Descripción"].astype(str).str.strip()
    df["Canal de comunicación"] = df["Canal de comunicación"].str.upper().str.strip()
    df["Mes apertura del caso"] = df["Mes apertura del caso"].astype(str)

    log.info(f"Registros válidos: {len(df)} (se eliminaron {nulos_antes} nulos)")
    return df


# ─── Paso 3: Clasificación automática ────────────────────────────────────────

def limpiar_texto(texto: str) -> str:
    texto = str(texto).upper()
    texto = re.sub(r'\d+', '', texto)
    texto = re.sub(r'[^\w\s]', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def clasificar(df: pd.DataFrame) -> pd.DataFrame:
    try:
        with open(f"{MODEL_PREFIX}_vectorizer.pkl", "rb") as f:
            vectorizer = pickle.load(f)
        with open(f"{MODEL_PREFIX}_lr.pkl", "rb") as f:
            modelo = pickle.load(f)

        textos = df["Descripción"].apply(limpiar_texto)
        X_vec = vectorizer.transform(textos)
        df["Categoria_Predicha"] = modelo.predict(X_vec)
        df["Probabilidad"] = modelo.predict_proba(X_vec).max(axis=1).round(3)
        log.info("Clasificación con modelo ML aplicada.")
    except FileNotFoundError:
        log.warning("Modelo no encontrado — usando clasificador de reglas.")
        df["Categoria_Predicha"] = df["Descripción"].apply(_clasificar_reglas)
        df["Probabilidad"] = 1.0

    return df


def _clasificar_reglas(texto: str) -> str:
    t = str(texto).upper()
    if ("PAGO" in t or "COBRO" in t or "MORA" in t) and "INCAPACIDAD" in t:
        return "DEMORA_PAGO_INCAPACIDAD"
    if "INCAPACIDAD" in t and any(w in t for w in ["ESTADO", "INFORMACIÓN", "INFORMACION", "SABER"]):
        return "CONSULTA_ESTADO_INCAPACIDAD"
    if "RADICADO" in t:
        return "SEGUIMIENTO_RADICADO"
    if "CERTIFICADO" in t:
        return "SOLICITUD_CERTIFICADO"
    if "ACCIDENTE" in t:
        return "ACCIDENTE_TRABAJO"
    if "INCAPACIDAD" in t:
        return "GESTION_INCAPACIDAD"
    return "OTRA_SOLICITUD"


# ─── Paso 4: Actualizar métricas ──────────────────────────────────────────────

def actualizar_metricas(df_nuevo: pd.DataFrame):
    """Añade los nuevos registros al histórico y recalcula métricas."""
    hist_path = DATA_DIR / "BD_Quejas_Analitica.xlsx"
    df_hist = pd.read_excel(hist_path)

    df_combinado = pd.concat([df_hist, df_nuevo], ignore_index=True)
    df_combinado.drop_duplicates(subset=["Descripción", "Nombre del cliente"], inplace=True)

    # Guardar histórico actualizado
    df_combinado.to_excel(hist_path, index=False)
    log.info(f"Histórico actualizado: {len(df_combinado)} registros totales")

    # Recalcular métricas
    metricas = {
        "total_quejas": len(df_combinado),
        "por_mes": df_combinado.groupby("Mes apertura del caso").size().to_dict(),
        "por_canal": df_combinado["Canal de comunicación"].value_counts().to_dict(),
    }
    return metricas, df_combinado


# ─── Paso 5: Generar reporte ──────────────────────────────────────────────────

def generar_reporte(df: pd.DataFrame, metricas: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"reporte_semanal_{timestamp}.xlsx"

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Quejas_Clasificadas", index=False)

        resumen = pd.DataFrame([
            {"Métrica": "Total quejas", "Valor": metricas["total_quejas"]},
            *[{"Métrica": f"Mes {k}", "Valor": v} for k, v in metricas["por_mes"].items()],
        ])
        resumen.to_excel(writer, sheet_name="Resumen", index=False)

    log.info(f"Reporte generado: {out_path}")
    return out_path


# ─── Orquestador principal ────────────────────────────────────────────────────

def ejecutar_pipeline(ruta_nuevos_datos: str = None):
    log.info("=" * 60)
    log.info("🚀 INICIANDO PIPELINE SEMANAL DE QUEJAS")
    log.info("=" * 60)

    try:
        # 1. Carga
        df_nuevo = cargar_nuevos_datos(ruta_nuevos_datos)

        # 2. Validación
        df_nuevo = validar_datos(df_nuevo)

        # 3. Clasificación
        df_nuevo = clasificar(df_nuevo)

        # 4. Actualizar histórico y métricas
        metricas, df_full = actualizar_metricas(df_nuevo)

        # 5. Generar reporte
        reporte = generar_reporte(df_nuevo, metricas)

        log.info("✅ Pipeline completado exitosamente")
        log.info(f"   Total quejas actualizadas: {metricas['total_quejas']}")
        log.info(f"   Reporte: {reporte}")

    except Exception as e:
        log.error(f"❌ Error en el pipeline: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    ejecutar_pipeline()
