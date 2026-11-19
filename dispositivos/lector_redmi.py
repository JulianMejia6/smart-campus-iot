
import json
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen

# Dirección del celular, recibida como argumento.
if len(sys.argv) != 2:
    print("Uso: python3 lector_redmi.py http://IP:8080")
    sys.exit(1)

PHONE_URL = sys.argv[1].rstrip("/")
DEVICE_ID = "REAL-01"
INTERVALO = 2  # Segundos entre consultas

print(f"Conectando con {DEVICE_ID}...")
print("Presiona Ctrl+C para detener.\n")

ultima_muestra = None

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

                    print(json.dumps(mensaje, indent=2))
                    ultima_muestra = identificador

        except Exception as error:
            print(f"Error de lectura: {error}")

        time.sleep(INTERVALO)

except KeyboardInterrupt:
    print("\nLectura detenida.")

