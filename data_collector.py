"""
Copyright (c) 2021 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

import requests
from influxdb_client import Point, InfluxDBClient
from urllib3 import Retry

from config import base_url, meraki_api_key, network_id, influx_url, token, org, bucket, temperature_sensors
from influxdb_client.client.write_api import SYNCHRONOUS

import pandas as pd
import time

# Influx DB Connector
retries = Retry(connect=10, read=5, redirect=10)
influx_client = InfluxDBClient(url=influx_url, token=token, org=org, retries=retries)
influx_db = influx_client.write_api(write_options=SYNCHRONOUS)


def get_latest_sensor_reading(sensor_serial, metric):
    """
    Get latest sensor reading from MT sensor
    metrics: 'temperature', 'humidity', 'water_detection' or 'door'
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Cisco-Meraki-API-Key": meraki_api_key
    }
    params = {
        "serials[]": sensor_serial,
        "metric": metric
    }
    try:
        msg = requests.request('GET',
                               f"{base_url}/networks/{network_id}/sensors/stats/latestBySensor",
                               headers=headers, params=params)
        if msg.ok:
            data = msg.json()
            return data
    except Exception as e:
        print("API Connection error: {}".format(e))


def get_historical_sensor_reading(sensor_serial, metric, timespan, resolution):
    """
    Get historical sensor readings from MT sensor
    The valid resolutions are: 1, 120, 3600, 14400, 86400. The default is 120.
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Cisco-Meraki-API-Key": meraki_api_key
    }

    params = {
        "serials[]": sensor_serial,
        "metric": metric,
        "timespan": timespan,
        "resolution": resolution,
        "agg": "max"
    }
    try:
        msg = requests.request('GET',
                               f"{base_url}/networks/{network_id}/sensors/stats/historicalBySensor",
                               headers=headers, params=params)
        if msg.ok:
            data = msg.json()
            return data
    except Exception as e:
        print("API Connection error: {}".format(e))


def get_sensor_name_mapping():
    """
    Get all sensor serials
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Cisco-Meraki-API-Key": meraki_api_key
    }

    try:
        msg = requests.request('GET', f"{base_url}/networks/{network_id}/sensors",
                               headers=headers)
        data = msg.json()
        sensor_name_mapping = {}
        for s in data["sensors"]:
            sensor_name_mapping[s["serial"]] = s["name"]
        return sensor_name_mapping
    except Exception as e:
        print("API Connection error: {}".format(e))


def get_shortened_sensor_name(sensor):
    return sensor[13:]


def checkLocation(sensor):
    if 'COLD' in sensor:
        return 'Cold'
    if 'HOT' in sensor:
        return 'Hot'


def put_historical_data_into_influx_temp_hum(sensor_serial, timespan, resolution):
    """
    Insert historical data into InfluxDB - temperature + humidity only
    """
    try:
        temperature_readings = get_historical_sensor_reading(sensor_serial, "temperature", timespan, resolution)
        df = pd.DataFrame(temperature_readings[0]["data"])

        df = df.rename(columns={"ts": "ts", "value": "temperature"})
        df = df.set_index("ts")

        humidity_readings = get_historical_sensor_reading(sensor_serial, "humidity", timespan, resolution)
        df_hum = pd.DataFrame(humidity_readings[0]["data"])
        df_hum = df_hum.rename(columns={"ts": "ts", "value": "humidity"})
        df_hum = df_hum.set_index("ts")

        df = pd.concat([df, df_hum], axis=1, join="inner")

    except Exception as e:
        print(f"{sensor_serial} - can't insert into dataframe: {e}")

    try:
        influx_db.write(
            bucket=bucket,
            org=org,
            record=df,
            data_frame_measurement_name=sensor_name_mapping[sensor_serial][13:], data_frame_tag_columns=['Location'])
        print(f"{sensor_serial} - Historical Temperature data successfully inserted.")
    except Exception as e:
        print(f"{sensor_serial} - can't write to database: {e}")


def main():
    print("** starting data collection *** ")

    global sensor_name_mapping
    sensor_name_mapping = get_sensor_name_mapping()

    for s in temperature_sensors:
        put_historical_data_into_influx_temp_hum(s, 2592000, 3600)  # last 30 days, sensor reading every 60 min, average

    while True:

        for s in temperature_sensors:
            try:

                r = get_latest_sensor_reading(s, "temperature")
                r_hum = get_latest_sensor_reading(s, "humidity")
                r = r[0]
                r_hum = r_hum[0]

                locationTag = checkLocation(sensor_name_mapping[s])
                influx_db.write(
                    bucket=bucket,
                    org=org,
                    record=Point(sensor_name_mapping[r["serial"]][13:])
                        .field("temperature", r["value"])
                        .field("humidity", r_hum["value"])
                        .time(r["ts"]).tag('Location', locationTag))
                print("**added to db**")
            except Exception as e:
                print("Can't write to database: {}".format(e))

        print("***time for sleep***")
        time.sleep(60)


main()


