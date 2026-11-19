
import json
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen

import paho.mqtt.client as mqtt

# Configuración
if len(sys.argv) != 2:
    print("Uso: python publicador_redmi.py http://IP:8080")
    sys.exit(1)

PHONE_URL = sys.argv[1].rstrip("/")
DEVICE_ID = "REAL-01"
TOPIC = "smart-campus/real/REAL-01/telemetry"
INTERVALO = 2

# Conexión al bróker MQTT local
cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="real01-bridge"
)

cliente.connect("127.0.0.1", 1883, 60)
cliente.loop_start()

ultima_muestra = None

print("Publicador MQTT iniciado.")
print(f"Dispositivo: {DEVICE_ID}")
print(f"Tema MQTT: {TOPIC}")
print("Presiona Ctrl+C para detener.\n")

try:
    while True:
        try:
            url = f"{PHONE_URL}/get?illum&illum_time"

            with urlopen(url, timeout=5) as respuesta:
                datos = json.load(respuesta)

            luz = datos["buffer"]["illum"]["buffer"]
            tiempos = datos["buffer"]["illum_time"]["buffer"]
            estado = datos["status"]

            if estado.get("measuring") and luz and tiempos:
                identificador = (
                    estado.get("session"),
                    tiempos[-1]
                )

                if identificador != ultima_muestra:
                    mensaje = {
                        "device_id": DEVICE_ID,
                        "type": "real",
                        "sensor": "ambient_light",
                        "value": round(float(luz[-1]), 2),
                        "unit": "lux",
                        "timestamp": datetime.now(
                            timezone.utc
                        ).isoformat(),
                        "experiment_time_s": tiempos[-1]
                    }

                    contenido = json.dumps(mensaje)

                    resultado = cliente.publish(
                        TOPIC,
                        contenido,
                        qos=1
                    )
                    resultado.wait_for_publish(timeout=5)

                    print(f"Publicado: {contenido}")
                    ultima_muestra = identificador

        except Exception as error:
            print(f"Error: {error}", file=sys.stderr)

        time.sleep(INTERVALO)

except KeyboardInterrupt:
    print("\nPublicador detenido.")

finally:
    cliente.disconnect()
    cliente.loop_stop()
