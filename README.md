# Smart Campus IoT

Proyecto académico de Internet de las Cosas (IoT).
Sistema distribuido de monitoreo ambiental, energético
y ocupacional desplegado en Microsoft Azure.

## Acceso a la plataforma

https://iot.crosshairmaker.app

El dashboard utiliza Grafana con autenticación.

## Arquitectura

Dispositivos y fuentes de datos
    ↓ HTTP / HTTPS / MQTT
Python (adquisición y publicación)
    ↓ MQTT
Eclipse Mosquitto
    ↓ MQTT
Servicio mqtt_a_influx.py
    ↓ InfluxDB API
InfluxDB 2.x
    ↓ Flux
Grafana

## Dispositivos

| ID | Tipo | Variables |
|---|---|---|
| REAL-01 | Sensor físico Redmi Note 13 | Luminosidad |
| TWIN-01 | Gemelo digital: Aula 101 | Temperatura, humedad, CO2, ocupación |
| TWIN-02 | Gemelo digital: Laboratorio | Temperatura, humedad, CO2, ocupación |
| TWIN-03 | Gemelo digital: Biblioteca | Temperatura, humedad, CO2, ocupación |
| TWIN-04 | Gemelo digital: Servidores | Temperatura, humedad, CO2, ocupación |
| API-01 | API: Bucaramanga | Temperatura, humedad, viento, precipitación |
| API-02 | API: Floridablanca | Temperatura, humedad, viento, precipitación |
| API-03 | API: Piedecuesta | Temperatura, humedad, viento, precipitación |
| DATA-01 | Dataset energético UCI | Energía, temperatura, humedad |
| DATA-02 | Dataset de ocupación UCI | Temperatura, humedad, luz, CO2, ocupación |

## Tecnologías

- Python 3
- Eclipse Mosquitto y MQTT
- HTTP y HTTPS
- InfluxDB 2.x y lenguaje Flux
- Grafana
- Docker y Docker Compose
- Ubuntu Server 24.04
- Microsoft Azure
- Caddy y HTTPS
- systemd para ejecución automática

## Ejecución

Instalar las dependencias:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Instalar y activar Mosquitto.

Iniciar los contenedores:

    cd infra
    sudo docker compose up -d

Configurar InfluxDB con la organización smart-campus
y el bucket telemetry.

Crear un token de escritura y configurar .env.local
tomando como referencia .env.example.

Los programas están organizados en:

- dispositivos/: adquisición, simulación y reproducción
- servicios/: receptor MQTT y almacenamiento
- infra/: Docker Compose y servicios systemd
- datos/datasets/: archivos CSV descargables
- docs/: documentación y evidencias

Los servicios systemd deben instalarse adaptando
las rutas de usuario cuando corresponda.

## Comunicación y control

Los dispositivos publican datos mediante MQTT
en temas smart-campus/<tipo>/<id>/telemetry.

Los gemelos digitales permiten modificar su estado
y su temperatura mediante mensajes MQTT de control.

Los dispositivos dataset permiten activar, pausar
y modificar la velocidad de reproducción.

Los estados se confirman mediante mensajes MQTT
en temas terminados en /state.

## Procedencia de datos

REAL-01 obtiene mediciones físicas del sensor del Redmi.

TWIN-01 a TWIN-04 generan valores simulados.

API-01 a API-03 consultan Open-Meteo.

DATA-01 y DATA-02 reproducen registros históricos
de UCI. La fecha de publicación no equivale a la fecha
original de medición.

Las fuentes dataset pueden descargarse nuevamente
con dispositivos/preparar_datasets.py.

## Fuentes de datos

Open-Meteo:
https://open-meteo.com/

UCI Appliances Energy Prediction:
https://archive.ics.uci.edu/dataset/374

UCI Occupancy Detection:
https://archive.ics.uci.edu/dataset/357

## Visualización

Grafana permite consultar series temporales,
promedios, mínimos, máximos y alertas.

Se implementó una regla experimental de temperatura
superior a 28 grados Celsius para TWIN-01.

## Seguridad

Los tokens, contraseñas, claves SSH y archivos .env.local
se excluyen del repositorio.

InfluxDB y Mosquitto no se exponen directamente
a Internet. El acceso web público utiliza HTTPS.
