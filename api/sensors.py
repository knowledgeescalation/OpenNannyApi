import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision

token = ';Y3"DZ2FmlFyR&32xrv,(l&@2KV5pB'
org = "domeczek"
url = "http://127.0.0.1:8086"

influx_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

bucket="niania"

query_api = influx_client.query_api()

def get_last():
    
    query = 'from(bucket:"niania")\
                |> range(start: -5m)\
                |> filter(fn: (r) => r["_measurement"] == "co2_sensor" or r["_measurement"] == "ups_sensor")\
                |> filter(fn: (r) => r["_field"] == "charge" or r["_field"] == "temperature" or r["_field"] == "humidity" or r["_field"] == "co2")\
                |> last()'

    result = query_api.query(org=org, query=query)

    sensor_dict = []
    for table in result:
        record = table.records[0]
        sensor_dict.append({'name': record.get_field(), 'value': str(record.get_value())})

    return sensor_dict

#print(get_last())
