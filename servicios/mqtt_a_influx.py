
import json
import os
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# Cargar configuración privada
ruta_env = Path(__file__).resolve().parent.parent / ".env.local"
load_dotenv(ruta_env)

URL = os.getenv("INFLUX_URL")
TOKEN = os.getenv("INFLUX_TOKEN")
ORG = os.getenv("INFLUX_ORG")
BUCKET = os.getenv("INFLUX_BUCKET")

if not all([URL, TOKEN, ORG, BUCKET]):
    raise SystemExit("Falta configurar .env.local")

# Conectar con InfluxDB
influx = InfluxDBClient(
    url=URL,
    token=TOKEN,
    org=ORG
)

if not influx.ping():
    raise SystemExit("InfluxDB no responde")

escritor = influx.write_api(write_options=SYNCHRONOUS)

TOPIC = "smart-campus/+/+/telemetry"


def al_conectar(cliente, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Conectado a Mosquitto")
        cliente.subscribe(TOPIC, qos=1)
        print(f"Suscrito a: {TOPIC}")
    else:
        print(f"Error MQTT: {reason_code}")


def al_recibir(cliente, userdata, mensaje):
    try:
        datos = json.loads(mensaje.payload.decode("utf-8"))

        fecha = datetime.fromisoformat(
            datos["timestamp"].replace("Z", "+00:00")
        )

        punto = (
            Point("iot_telemetry")
            .tag("device_id", str(datos["device_id"]))
            .tag("sensor", str(datos["sensor"]))
            .tag("type", str(datos.get("type", "unknown")))
            .field("value", float(datos["value"]))
            .time(fecha, WritePrecision.NS)
        )

        escritor.write(
            bucket=BUCKET,
            org=ORG,
            record=punto
        )

        print(
            f"Guardado: {datos['device_id']} | "
            f"{datos['sensor']} = {datos['value']}"
        )

    except Exception as error:
        print(f"Error guardando mensaje: {error}")


cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart-campus-influx-writer"
)

cliente.on_connect = al_conectar
cliente.on_message = al_recibir

try:
    cliente.connect("127.0.0.1", 1883, 60)
    print("Iniciando almacenamiento MQTT → InfluxDB...")
    cliente.loop_forever()

except KeyboardInterrupt:
    print("\nAlmacenamiento detenido.")

finally:
    cliente.disconnect()
    influx.close()

