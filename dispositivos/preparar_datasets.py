
import csv
import io
import zipfile
from pathlib import Path
from urllib.request import urlopen

BASE = Path.home() / "smart-campus-iot" / "datos" / "datasets"
BASE.mkdir(parents=True, exist_ok=True)

FUENTES = {
    "DATA-01": {
        "url": "https://archive.ics.uci.edu/static/public/374/appliances+energy+prediction.zip",
        "archivo": "energydata_complete.csv",
        "variables": {
            "temperature": "T1",
            "humidity": "RH_1",
            "appliance_energy_wh": "Appliances",
        },
    },
    "DATA-02": {
        "url": "https://archive.ics.uci.edu/static/public/357/occupancy+detection.zip",
        "archivo": "datatraining.txt",
        "variables": {
            "temperature": "Temperature",
            "humidity": "Humidity",
            "light": "Light",
            "co2": "CO2",
            "occupancy": "Occupancy",
        },
    },
}

for dispositivo, config in FUENTES.items():
    print(f"Descargando {dispositivo}...")

    with urlopen(config["url"], timeout=90) as respuesta:
        contenido = respuesta.read()

    with zipfile.ZipFile(io.BytesIO(contenido)) as comprimido:
        nombre = next(
            n for n in comprimido.namelist()
            if n.endswith(config["archivo"])
        )

        with comprimido.open(nombre) as archivo:
            texto = io.TextIOWrapper(archivo, encoding="utf-8")
            lector = csv.DictReader(texto)
            if dispositivo == "DATA-02":
                lector.fieldnames = ["row_id"] + lector.fieldnames

            destino = BASE / f"{dispositivo}.csv"
            columnas = ["source_time"] + list(config["variables"])

            with destino.open("w", newline="", encoding="utf-8") as salida:
                escritor = csv.DictWriter(salida, fieldnames=columnas)
                escritor.writeheader()

                total = 0

                for fila in lector:
                    try:
                        registro = {"source_time": fila["date"]}

                        for variable, columna in config["variables"].items():
                            registro[variable] = float(fila[columna])

                        escritor.writerow(registro)
                        total += 1

                    except (ValueError, KeyError, TypeError):
                        continue

                    if total >= 1000:
                        break

    print(f"{dispositivo}: {total} registros preparados")
    print(f"Guardado en {destino}")

print("Datasets preparados correctamente.")

