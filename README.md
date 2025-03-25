**OpenNannyApi** is an open-source baby monitoring system designed to run on Raspberry Pi devices. This project combines environmental sensors, audio/video streaming capabilities, and a RESTful API to create a comprehensive monitoring solution for baby rooms. For full tutorial visit: https://knowledgeescalation.com/posts/open-nanny.

## Features
- **Environmental Monitoring**: Real-time tracking of CO2 levels, temperature, and humidity
- **Power Management**: UPS status monitoring (voltage, current, power, and charge percentage)
- **Video Streaming**: Live video feed with night mode capability via WebRTC
- **LED Control**: Remote control of IR LEDs
- **Audio Streaming**: One-way audio communication
- **Music Player**: Integrated MP3 player
- **Secure API**: JWT authentication for all endpoints
- **Data Storage**: Time-series data storage using InfluxDB

## Hardware Requirements

- Raspberry Pi Zero 2 WH,
- SD card with Raspbian,
- [DFRobot SEN0536 (sensor: co2, temperature, humidity)](https://wiki.dfrobot.com/SKU_SEN0536_Gravity_SCD41_Infrared_CO2_Sensor#target_9),
- 2x [SPH0645LM4H (I2S MEMS microphone)](https://learn.adafruit.com/adafruit-i2s-mems-microphone-breakout/raspberry-pi-wiring-test),
- [MAX98357A (I2S amplifier)](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/raspberry-pi-wiring),
- 2x [speaker 1w 8 ohm](https://www.granvozchina.com/info/how-to-wire-speakers-in-parallel-series-and-98026087.html),
- 24LC256 EEPROM (you need only 128 bytes),
- CSI camera with IR cut (ov5647),
- 2x 3W IR leds,
- 2x NPN transistors (2N2222),
- 2x 1kΩ resistors,
- [Raspberry Pi Zero UPS HAT (Waveshare 19739)](https://www.waveshare.com/wiki/UPS_HAT_(C)),
- battery 3.7 V 4000mAh,
- camera case,
- OpenNanny case.

## Software Dependencies

- Python 3.8+
- InfluxDB (time-series database)
- FastAPI (web framework)
- aiortc (WebRTC implementation)
- PyAudio (audio handling)
- pygame (music playback)
- picamera2 (camera interface)
- OpenCV (image processing)
- passlib & jwt (authentication)
- smbus (I2C communication)


## Instalation

1. Clone the repository:
```bash
git clone https://github.com/knowledgeescalation/OpenNannyApi.git
cd OpenNannyApi
```

2. Setup Influx Database.

3. Install required packages for sensors:
```bash
cd sensors
python -m venv env
. env/bin/activate
pip install -r requirements.txt
```

4. Install required packages for api:
```bash
cd api
python -m venv env
. env/bin/activate
pip install -r requirements.txt
```
5. Set up your environment variables in a sensors/.env file:
   
```python
token=your_influxdb_token
influx_org=your_organization
influx_bucket=your_bucket
```

6. Set up your environment variables in a api/.env file:

Prepare api/.env file.
```python
SECRET_KEY=your_jwt_secret_key

USER_NAME=api_username
FULL_USER_NAME=Your Full Name
USER_EMAIL=your@email.com

USER_HASH=bcrypt_hashed_password

MUSIC_PATH=/path/to/mp3/files
```

## Usage

Starting the API Server

```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```

Starting the Sensor Monitoring Script
```bash
cd sensors
python script.py
```


## API Endpoints

**Authentication**
- `POST /token` - Obtain JWT token with username/password

**Sensor Data**
- `GET /sensors` - Get latest sensor readings (CO2, temperature, humidity, battery)

**LED Control**
- `POST /led` - Control night light LEDs
  - Commands: `status`, `night`, `day`

**Music Control**
- `POST /music` - Control music playback
  - Commands: `lsdir`, `lsmp3`, `play`, `pause`, `unpause`, `stop`, `status`, `set_volume`, `rewind`

**Video/Audio Streaming**
- `WebSocket /webrtc` - WebRTC connection for video/audio streaming

## WebRTC Implementation

The system uses WebRTC for low-latency video and audio streaming. The implementation includes:
- Video stream from Raspberry Pi Camera
- Audio stream from I2S MEMS microphone
- Night mode for improved visibility in dark environments
- On-screen timestamp for monitoring purposes

## Data Storage

Sensor data is stored in InfluxDB with the following measurement structure:
- `co2_sensor` - CO2 (ppm), temperature (°C), humidity (% RH)
- `ups_sensor` - voltage (V), current (A), power (W), charge (%)

Data is collected every 60 seconds and can be queried via the InfluxDB API or the `/sensors` endpoint.

