#!/usr/bin/env python3
"""Predicción académica de temperatura de TWIN-01 a partir de InfluxDB.

Los datos de TWIN-01 son simulados. Un modelo no implica predicción
validada de la temperatura de un aula real.
"""

import json
import os
from datetime import timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "analisis"
SALIDA.mkdir(parents=True, exist_ok=True)

load_dotenv(RAIZ / ".env.local")
URL = os.getenv("INFLUX_URL", "http://127.0.0.1:8086")
ORGANIZACION = os.getenv("INFLUX_ORG", "smart-campus")
BUCKET = os.getenv("INFLUX_BUCKET", "telemetry")
TOKEN = os.getenv("INFLUX_READ_TOKEN") or os.getenv("INFLUX_TOKEN")

if not TOKEN:
    raise SystemExit("Falta INFLUX_TOKEN o INFLUX_READ_TOKEN en .env.local")

# BUCKET es un nombre controlado por la configuración local. Se escapa para Flux.
BUCKET_FLUX = json.dumps(BUCKET)
consulta = f'''
from(bucket: {BUCKET_FLUX})
  |> range(start: -8d)
  |> filter(fn: (r) => r._measurement == "iot_telemetry")
  |> filter(fn: (r) => r._field == "value")
  |> filter(fn: (r) => r.device_id == "TWIN-01")
  |> filter(fn: (r) => r.sensor == "temperature")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
  |> keep(columns: ["_time", "_value"])
'''

print(f"Consultando InfluxDB: bucket={BUCKET!r}, org={ORGANIZACION!r}, url={URL!r}")
try:
    with InfluxDBClient(url=URL, token=TOKEN, org=ORGANIZACION, timeout=60000) as cliente:
        tablas = cliente.query_api().query(consulta, org=ORGANIZACION)
except Exception as exc:
    detalle = str(exc)
    if 'could not find bucket' in detalle:
        raise SystemExit(
            f"InfluxDB no encuentra el bucket {BUCKET!r}. "
            "Revisa el nombre real en InfluxDB (Load Data > Buckets) "
            "y corrige INFLUX_BUCKET en .env.local."
        ) from None
    if 'unauthorized' in detalle.lower() or '(401)' in detalle or '(403)' in detalle:
        raise SystemExit(
            "El token no tiene permiso para consultar ese bucket; "
            "usa un token de lectura válido en .env.local."
        ) from None
    raise

# Una medición por intervalo, con fechas ordenadas.
registros = sorted(
    {(r.get_time(), float(r.get_value())) for tabla in tablas for r in tabla.records},
    key=lambda elemento: elemento[0]
)
if len(registros) < 100:
    raise SystemExit(f"Se encontraron solo {len(registros)} ventanas de 5 minutos; se requieren al menos 100.")

fechas = [f for f, _ in registros]
valores = np.array([v for _, v in registros], dtype=float)

# Cada fila predice el siguiente intervalo a partir de 12 observaciones anteriores.
# Solo se utilizan secuencias continuas; no se mezclan pausas de captura.
X, y, fechas_objetivo = [], [], []
for indice in range(12, len(registros)):
    tramo = fechas[indice - 12:indice + 1]
    diferencias = [(b - a).total_seconds() for a, b in zip(tramo, tramo[1:])]
    if not all(0 < delta <= 600 for delta in diferencias):
        continue
    previo = valores[indice - 12:indice]
    X.append([
        float(previo[-1]), float(previo[-2]), float(previo[-3]),
        float(np.mean(previo[-6:])), float(np.mean(previo))
    ])
    y.append(float(valores[indice]))
    fechas_objetivo.append(fechas[indice])

if len(X) < 60:
    raise SystemExit(
        f"Solo hay {len(X)} ventanas de entrenamiento contiguas. "
        "Comprueba si el gemelo ha publicado datos suficientes sin grandes interrupciones."
    )

X = np.asarray(X)
y = np.asarray(y)
corte = int(len(X) * 0.8)
modelo = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=2)
modelo.fit(X[:corte], y[:corte])
predicciones = modelo.predict(X[corte:])
mae_ia = float(mean_absolute_error(y[corte:], predicciones))
mae_referencia = float(mean_absolute_error(y[corte:], X[corte:, 0]))

# Para pronosticar 'próximos 5 minutos', el historial reciente debe ser continuo.
tramo_final = fechas[-12:]
if not all(0 < (b - a).total_seconds() <= 600 for a, b in zip(tramo_final, tramo_final[1:])):
    raise SystemExit("El tramo más reciente tiene discontinuidades: no se generó pronóstico futuro.")
previo = valores[-12:]
caracteristica_final = [[
    float(previo[-1]), float(previo[-2]), float(previo[-3]),
    float(np.mean(previo[-6:])), float(np.mean(previo))
]]
pronostico = float(modelo.predict(caracteristica_final)[0])
fecha_pronostico = fechas[-1] + timedelta(minutes=5)

resultado = {
    "dispositivo": "TWIN-01",
    "tipo_fuente": "Gemelo digital: datos simulados",
    "variable": "temperature",
    "horizonte_prediccion_minutos": 5,
    "observaciones_agrupadas": int(len(valores)),
    "ejemplos_supervisados": int(len(X)),
    "ejemplos_entrenamiento": int(corte),
    "ejemplos_evaluacion": int(len(y) - corte),
    "inicio_utc": fechas[0].isoformat(),
    "ultima_observacion_utc": fechas[-1].isoformat(),
    "fecha_pronostico_utc": fecha_pronostico.isoformat(),
    "temperatura_ultima_c": float(valores[-1]),
    "prediccion_c": pronostico,
    "mae_random_forest_c": mae_ia,
    "mae_persistencia_c": mae_referencia,
    "advertencia": "Modelo entrenado con datos simulados, sin validación en edificios reales."
}
(SALIDA / "resultado_prediccion.json").write_text(
    json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8"
)

n = min(144, len(registros))
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(fechas[-n:], valores[-n:], label="Temperatura simulada (5 min)")
ax.scatter([fecha_pronostico], [pronostico], marker="x", s=120, label="Pronóstico +5 min")
ax.set(title="Smart Campus IoT — predicción TWIN-01", xlabel="Fecha (UTC)", ylabel="Temperatura (°C)")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M", tz=fechas[-1].tzinfo))
ax.tick_params(axis="x", rotation=25)
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(SALIDA / "prediccion_temperatura.png", dpi=160)
plt.close(fig)

print("\n=== RESULTADOS ===")
print(f"Observaciones de 5 min: {len(registros)}")
print(f"Ejemplos entrenados: {corte} | evaluados: {len(y) - corte}")
print(f"Última temperatura simulada: {valores[-1]:.2f} °C")
print(f"Predicción para {fecha_pronostico.isoformat()}: {pronostico:.2f} °C")
print(f"MAE Random Forest: {mae_ia:.3f} °C")
print(f"MAE predicción por persistencia: {mae_referencia:.3f} °C")
print(f"Resultado: {SALIDA / 'resultado_prediccion.json'}")
print(f"Gráfica: {SALIDA / 'prediccion_temperatura.png'}")
