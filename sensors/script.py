import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from DFRobot_SCD4X import *
from UPS import INA219

from dotenv import load_dotenv

load_dotenv()

token = os.getenv('token')
org = os.getenv('influx_org')
url = "http://127.0.0.1:8086"

influx_client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

bucket = os.getenv('influx_bucket')

write_influx_api = influx_client.write_api(write_options=SYNCHRONOUS)

sensor = DFRobot_SCD4X(i2c_addr = SCD4X_I2C_ADDR, bus = 1)
ina219 = INA219(addr=0x43)

def write_data(category, field, value):

    point = (Point(category).field(pole, value))
    write_api.write(bucket=bucket, org=org, record=point)


def setup_co2():
    while (not sensor.begin):
        print ('Please check that the CO2 sensor is properly connected.')
        time.sleep(3)
  
    print("CO2 sensor begin successfully!!!")

    sensor.enable_period_measure(SCD4X_STOP_PERIODIC_MEASURE)

    #sensor.set_temp_comp(4.0)

    print("The current temperature compensation value : %0.2f C" %(sensor.get_temp_comp))

    sensor.set_sensor_altitude(130)

    print("Set the current environment altitude : %u m" %(sensor.get_sensor_altitude))

    if(sensor.get_auto_calib_mode):
        print("Automatic calibration on!")
    else:
        print("Automatic calibration off!")

    sensor.enable_period_measure(SCD4X_START_PERIODIC_MEASURE)

def get_co2_data():

    while not sensor.get_data_ready_status:
        print('Waiting for co2 data...')
        time.sleep(1)


    CO2ppm, temp, humidity = sensor.read_measurement

    return CO2ppm, temp, humidity

def get_ups_data():

    bus_voltage = ina219.getBusVoltage_V()             # voltage on V- (load side)
    shunt_voltage = ina219.getShuntVoltage_mV() / 1000 # voltage between V+ and V- across the shunt
    current = ina219.getCurrent_mA()                   # current in mA
    power = ina219.getPower_W()                        # power in W
    p = (bus_voltage - 3)/1.2*100
    if(p > 100):p = 100
    if(p < 0):p = 0

    return bus_voltage, current/1000, power, p 


setup_co2()

while True:

    time.sleep(60)

    CO2ppm, temp, humidity = get_co2_data()
    bus_voltage, current, power, p = get_ups_data()
    
    point_co2 = Point('co2_sensor').field('co2', CO2ppm).field('temperature', float("%0.2f"%temp)).field('humidity', float("%0.2f"%humidity))
    point_ups = Point('ups_sensor').field('volatage', float('{:6.3f}'.format(bus_voltage))).field('current', float('{:6.3f}'.format(current))).field('power', float('{:6.3f}'.format(power))).field('charge', float('{:3.1f}'.format(p)))

    write_influx_api.write(bucket=bucket, org=org, record=(point_co2, point_ups))

    #print(point_co2)
    #print(point_ups)
    #print("")

    #print("Carbon dioxide concentration : %u ppm" %CO2ppm)
    #print("Environment temperature : %0.2f C" %temp)
    #print("Relative humidity : %0.2f RH" %humidity)

    #print("Load Voltage:  {:6.3f} V".format(bus_voltage))
    #print("Current:       {:6.3f} A".format(current))
    #print("Power:         {:6.3f} W".format(power))
    #print("Percent:       {:3.1f}%".format(p))
    #print("")




