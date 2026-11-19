import json
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError

import paho.mqtt.client as mqtt


BROKER = "127.0.0.1"
PUERTO = 1883
INTERVALO = 600  # Consultar la API cada 10 minutos

ESTACIONES = {
    "API-01": {
        "nombre": "Bucaramanga",
        "lat": 7.1193,
        "lon": -73.1227,
    },
    "API-02": {
        "nombre": "Floridablanca",
        "lat": 7.0631,
        "lon": -73.0860,
    },
    "API-03": {
        "nombre": "Piedecuesta",
        "lat": 6.9894,
        "lon": -73.0495,
    },
}

VARIABLES = {
    "temperature_2m": "temperature",
    "relative_humidity_2m": "humidity",
    "wind_speed_10m": "wind_speed",
    "precipitation": "precipitation",
}


def consultar_api(latitud, longitud):
    parametros = urlencode({
        "latitude": latitud,
        "longitude": longitud,
        "current": ",".join(VARIABLES.keys()),
        "timezone": "UTC",
    })

    url = f"https://api.open-meteo.com/v1/forecast?{parametros}"

    solicitud = Request(
        url,
        headers={"User-Agent": "SmartCampusIoT/1.0"},
    )

    with urlopen(solicitud, timeout=20) as respuesta:
        return json.load(respuesta)


cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart-campus-estaciones-api",
)

cliente.connect(BROKER, PUERTO, 60)
cliente.loop_start()

print("Iniciando estaciones meteorologicas API...")


try:
    while True:
        for dispositivo, estacion in ESTACIONES.items():

            try:
                datos = consultar_api(
                    estacion["lat"],
                    estacion["lon"],
                )

                actuales = datos["current"]
                timestamp = datetime.now(timezone.utc).isoformat()

                for variable_api, nombre_sensor in VARIABLES.items():
                    valor = actuales.get(variable_api)

                    if not isinstance(valor, (int, float)):
                        continue

                    lectura = {
                        "device_id": dispositivo,
                        "type": "api",
                        "sensor": nombre_sensor,
                        "value": valor,
                        "timestamp": timestamp,
                        "source_time": actuales.get("time"),
                    }

                    tema = (
                        f"smart-campus/api/"
                        f"{dispositivo}/telemetry"
                    )

                    cliente.publish(
                        tema,
                        json.dumps(lectura),
                        qos=1,
                    )

                print(
                    f"{dispositivo} "
                    f"({estacion['nombre']}): {actuales}"
                )

            except (URLError, TimeoutError, ValueError, KeyError) as error:
                print(
                    f"Error consultando {dispositivo}: {error}"
                )

        print("Proxima consulta en 10 minutos...")
        time.sleep(INTERVALO)

except KeyboardInterrupt:
    print("\nDeteniendo estaciones API...")

finally:
    cliente.disconnect()
    cliente.loop_stop()
