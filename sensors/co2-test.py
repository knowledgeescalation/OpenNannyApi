from __future__ import print_function
import sys
import os

from DFRobot_SCD4X import *

sensor = DFRobot_SCD4X(i2c_addr = SCD4X_I2C_ADDR, bus = 1)

def setup():
    while (not sensor.begin):
        print ('Please check that the device is properly connected')
        time.sleep(3)
  
    print("Sensor begin successfully!!!")

    sensor.enable_period_measure(SCD4X_STOP_PERIODIC_MEASURE)

    #sensor.set_temp_comp(4.0)

    print("The current temperature compensation value : %0.2f C" %(sensor.get_temp_comp))

    #sensor.set_sensor_altitude(130)

    print("Set the current environment altitude : %u m" %(sensor.get_sensor_altitude))

    if(sensor.get_auto_calib_mode):
        print("Automatic calibration on!")
    else:
        print("Automatic calibration off!")

    sensor.enable_period_measure(SCD4X_START_PERIODIC_MEASURE)
    
def loop():

    if(sensor.get_data_ready_status):
        CO2ppm, temp, humidity = sensor.read_measurement

        print("Carbon dioxide concentration : %u ppm" %CO2ppm)
        print("Environment temperature : %0.2f C" %temp)
        print("Relative humidity : %0.2f RH\n" %humidity)

    time.sleep(1)


setup()
while True:
    loop()
