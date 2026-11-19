import json
import math
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


BROKER = "127.0.0.1"
PUERTO = 1883
INTERVALO = 20

# ID: nombre, temperatura base, humedad base, CO2 base, capacidad
AMBIENTES = {
    "TWIN-01": ("Aula 101", 25.0, 60, 420, 30),
    "TWIN-02": ("Laboratorio", 24.0, 55, 430, 25),
    "TWIN-03": ("Biblioteca", 23.5, 58, 410, 40),
    "TWIN-04": ("Sala de servidores", 21.0, 45, 400, 5),
}

estados = {
    dispositivo: {"enabled": True, "temp_offset": 0.0}
    for dispositivo in AMBIENTES
}

ocupaciones = {
    dispositivo: capacidad // 3
    for dispositivo, (_, _, _, _, capacidad) in AMBIENTES.items()
}


def fecha_actual():
    return datetime.now(timezone.utc).isoformat()


def al_conectar(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Gemelos conectados a Mosquitto")
        client.subscribe("smart-campus/twin/+/control", qos=1)
        print("Esperando comandos de control...")
    else:
        print("Error de conexion:", reason_code)


def al_recibir(client, userdata, mensaje):
    dispositivo = mensaje.topic.split("/")[2]

    if dispositivo not in estados:
        return

    try:
        comando = json.loads(mensaje.payload.decode())

        if not isinstance(comando, dict):
            return

        if isinstance(comando.get("enabled"), bool):
            estados[dispositivo]["enabled"] = comando["enabled"]

        ajuste = comando.get("temp_offset")

        if isinstance(ajuste, (int, float)) and not isinstance(ajuste, bool):
            estados[dispositivo]["temp_offset"] = max(-10, min(10, ajuste))

        respuesta = {
            "device_id": dispositivo,
            **estados[dispositivo],
            "timestamp": fecha_actual(),
        }

        client.publish(
            f"smart-campus/twin/{dispositivo}/state",
            json.dumps(respuesta),
            qos=1,
            retain=True,
        )

        print("Configuracion actualizada:", respuesta)

    except (ValueError, UnicodeDecodeError) as error:
        print("Comando invalido:", error)


cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart-campus-gemelos",
)

cliente.on_connect = al_conectar
cliente.on_message = al_recibir

cliente.connect(BROKER, PUERTO, 60)
cliente.loop_start()

print("Iniciando cuatro gemelos digitales...")


try:
    while True:
        instante = time.time()

        for indice, (dispositivo, datos) in enumerate(AMBIENTES.items()):
            nombre, temp_base, humedad_base, co2_base, capacidad = datos

            if not estados[dispositivo]["enabled"]:
                continue

            # Ocupacion variable, dentro de la capacidad del espacio.
            ocupaciones[dispositivo] = max(
                0,
                min(
                    capacidad,
                    ocupaciones[dispositivo] + random.choice([-2, -1, 0, 0, 1, 2]),
                ),
            )

            ocupacion = ocupaciones[dispositivo]

            temperatura = round(
                temp_base
                + math.sin(instante / 180 + indice)
                + estados[dispositivo]["temp_offset"]
                + random.uniform(-0.3, 0.3),
                2,
            )

            humedad = round(
                max(
                    0,
                    min(
                        100,
                        humedad_base
                        + 3 * math.sin(instante / 250 + indice)
                        + random.uniform(-1, 1),
                    ),
                ),
                2,
            )

            co2 = round(
                max(350, co2_base + ocupacion * 18 + random.uniform(-15, 15)),
                2,
            )

            variables = {
                "temperature": temperatura,
                "humidity": humedad,
                "co2": co2,
                "occupancy": ocupacion,
            }

            for sensor, valor in variables.items():
                lectura = {
                    "device_id": dispositivo,
                    "type": "digital_twin",
                    "sensor": sensor,
                    "value": valor,
                    "timestamp": fecha_actual(),
                }

                cliente.publish(
                    f"smart-campus/twin/{dispositivo}/telemetry",
                    json.dumps(lectura),
                    qos=1,
                )

            print(f"{dispositivo} ({nombre}): {variables}")

        time.sleep(INTERVALO)

except KeyboardInterrupt:
    print("\nDeteniendo gemelos digitales...")

finally:
    cliente.disconnect()
    cliente.loop_stop()
