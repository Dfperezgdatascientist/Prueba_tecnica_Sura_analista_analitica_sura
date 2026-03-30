# Flujo Automatizado del Proceso Semanal de Quejas

Este documento describe el flujo automatizado implementado en el archivo `pipeline/pipeline_semanal.py` para la actualización, clasificación y reporte semanal de quejas en la empresa. El objetivo es mantener actualizados los datos, métricas y reportes, facilitando la toma de decisiones y el monitoreo continuo.

---

## 1. Descripción General

El pipeline semanal automatiza las siguientes tareas:

1. **Carga de nuevos datos**: Obtiene los registros recientes de quejas desde un archivo Excel, API, base de datos o simulación.
2. **Limpieza y validación**: Verifica la integridad de los datos, elimina registros nulos y estandariza formatos.
3. **Clasificación automática**: Asigna una categoría a cada queja usando un modelo de Machine Learning entrenado o, en su defecto, reglas heurísticas.
4. **Actualización de métricas**: Fusiona los nuevos datos con el histórico, elimina duplicados y recalcula métricas clave.
5. **Generación de reportes**: Exporta los resultados y métricas a archivos Excel para su análisis y seguimiento.
6. **Notificación y logging**: Registra el proceso en logs y puede enviar alertas por email (en producción).

---

## 2. Detalle de los Pasos

### Paso 1: Carga de Nuevos Datos
- Se busca un archivo de datos nuevos (por ruta o integración).
- Si no se encuentra, se simula la llegada de datos usando las últimas filas del histórico.
- En producción, puede conectarse a APIs, bases de datos o SFTP.

### Paso 2: Limpieza y Validación
- Se verifica que existan todas las columnas requeridas.
- Se eliminan registros nulos en campos críticos.
- Se estandarizan los formatos de texto y fechas.

### Paso 3: Clasificación Automática
- Si existe un modelo ML entrenado, se utiliza para predecir la categoría de cada queja.
- Si no, se aplican reglas basadas en palabras clave para clasificar.
- Se calcula la probabilidad de la predicción (si aplica).

### Paso 4: Actualización de Métricas
- Se combinan los nuevos datos con el histórico, eliminando duplicados.
- Se recalculan métricas como total de quejas, distribución por mes y canal.
- Se actualiza el archivo histórico principal.

### Paso 5: Generación de Reportes
- Se exportan los datos clasificados y un resumen de métricas a un archivo Excel con timestamp.
- El reporte incluye hojas separadas para datos y resumen.

### Paso 6: Notificación y Logging
- Todo el proceso queda registrado en un archivo de log (`outputs/pipeline.log`).
- En producción, se pueden enviar alertas por email si se detectan condiciones críticas (volumen alto, nuevas categorías, etc.).

---

## 3. Configuración

La configuración del pipeline se encuentra en `pipeline/config.yaml` e incluye:
- Frecuencia de ejecución (cron, zona horaria)
- Fuentes de datos y rutas
- Columnas requeridas y reglas de validación
- Parámetros de clasificación y métricas
- Opciones de notificación y alertas

---

## 4. Orquestación y Automatización

- El pipeline puede ejecutarse manualmente (`python pipeline/pipeline_semanal.py`) o programarse con herramientas como Apache Airflow, GitHub Actions o tareas programadas del sistema.
- El flujo es robusto ante errores: si ocurre una excepción, se registra en el log y se detiene el proceso.

---

## 5. Extensiones y Producción

- En ambientes productivos, se recomienda usar orquestadores (Airflow, Lambda, CI/CD) y activar notificaciones por email.
- El pipeline es fácilmente extensible para nuevas fuentes de datos, métricas o reportes.

---

## 6. Archivos Clave
- `pipeline/pipeline_semanal.py`: Script principal del flujo semanal.
- `pipeline/config.yaml`: Configuración del pipeline.
- `outputs/pipeline.log`: Registro de ejecución y errores.
- `outputs/reporte_semanal_*.xlsx`: Reportes generados automáticamente.
- `data/BD_Quejas_Analitica.xlsx`: Histórico principal de quejas.

---

## 7. Diagrama del Flujo de Automatización

``` mermaid
flowchart TD
    A[Inicio Pipeline] --> B[Cargar nuevos datos]
    B --> C[Limpieza y validación]
    C --> D{¿Modelo ML disponible?}
    D -- Sí --> E[Clasificación ML]
    D -- No --> F[Clasificación por reglas]
    E --> G[Actualizar histórico y métricas]
    F --> G
    G --> H[Generar reporte Excel]
    H --> I[Registrar log / Notificar]
    I --> J[Fin Pipeline]
```

---

**Autor:** Equipo de Analítica — 2026
