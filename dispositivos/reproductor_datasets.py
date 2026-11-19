
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt


BASE = Path(__file__).resolve().parent.parent
CARPETA = BASE / "datos" / "datasets"

BROKER = "127.0.0.1"
PUERTO = 1883

DISPOSITIVOS = {
    "DATA-01": {
        "nombre": "Consumo energetico residencial",
        "archivo": "DATA-01.csv",
    },
    "DATA-02": {
        "nombre": "Ocupacion de oficina",
        "archivo": "DATA-02.csv",
    },
}

datos = {}
estados = {}

# Cargar registros historicos
for dispositivo, configuracion in DISPOSITIVOS.items():

    ruta = CARPETA / configuracion["archivo"]

    with ruta.open(encoding="utf-8", newline="") as archivo:
        registros = list(csv.DictReader(archivo))

    if not registros:
        raise RuntimeError(f"Dataset vacio: {dispositivo}")

    datos[dispositivo] = registros

    estados[dispositivo] = {
        "enabled": True,
        "interval_s": 60,
        "index": 0,
        "next_at": 0.0,
    }

    print(f"{dispositivo}: {len(registros)} registros cargados")


def fecha_actual():
    return datetime.now(timezone.utc).isoformat()


def publicar_estado(cliente, dispositivo):

    estado = estados[dispositivo]

    respuesta = {
        "device_id": dispositivo,
        "enabled": estado["enabled"],
        "interval_s": estado["interval_s"],
        "index": estado["index"],
        "timestamp": fecha_actual(),
    }

    cliente.publish(
        f"smart-campus/dataset/{dispositivo}/state",
        json.dumps(respuesta),
        qos=1,
        retain=True,
    )

    print("Estado:", respuesta)


def al_conectar(cliente, userdata, flags, reason_code, properties):

    if reason_code == 0:
        print("Reproductores conectados a MQTT")

        cliente.subscribe(
            "smart-campus/dataset/+/control",
            qos=1,
        )

        for dispositivo in estados:
            publicar_estado(cliente, dispositivo)


def al_recibir(cliente, userdata, mensaje):

    dispositivo = mensaje.topic.split("/")[2]

    if dispositivo not in estados:
        return

    try:
        comando = json.loads(mensaje.payload.decode())

        if not isinstance(comando, dict):
            return

        estado = estados[dispositivo]

        if isinstance(comando.get("enabled"), bool):
            estado["enabled"] = comando["enabled"]

        intervalo = comando.get("interval_s")

        if (
            isinstance(intervalo, (int, float))
            and not isinstance(intervalo, bool)
            and 5 <= intervalo <= 3600
        ):
            estado["interval_s"] = float(intervalo)

        if comando.get("reset") is True:
            estado["index"] = 0

        estado["next_at"] = 0.0

        publicar_estado(cliente, dispositivo)

    except (ValueError, UnicodeDecodeError) as error:
        print("Comando invalido:", error)


cliente = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart-campus-datasets",
)

cliente.on_connect = al_conectar
cliente.on_message = al_recibir

cliente.connect(BROKER, PUERTO, 60)
cliente.loop_start()

print("Reproductores iniciados...")


try:
    while True:

        ahora = time.monotonic()

        for dispositivo, estado in estados.items():

            if not estado["enabled"]:
                continue

            if ahora < estado["next_at"]:
                continue

            registros = datos[dispositivo]
            indice = estado["index"] % len(registros)
            registro = registros[indice]

            timestamp = fecha_actual()

            for variable, valor in registro.items():

                if variable == "source_time":
                    continue

                mensaje = {
                    "device_id": dispositivo,
                    "type": "dataset",
                    "sensor": variable,
                    "value": float(valor),
                    "timestamp": timestamp,
                    "source_time": registro["source_time"],
                    "replay": True,
                }

                cliente.publish(
                    f"smart-campus/dataset/{dispositivo}/telemetry",
                    json.dumps(mensaje),
                    qos=1,
                )

            estado["index"] += 1
            estado["next_at"] = (
                ahora + estado["interval_s"]
            )

            print(
                f"{dispositivo}: registro "
                f"{indice + 1}/{len(registros)} "
                f"publicado"
            )

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nDeteniendo reproductores...")

finally:
    cliente.disconnect()
    cliente.loop_stop()

