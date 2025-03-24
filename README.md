**OpenNannyApi** is an open-source baby monitoring system designed to run on Raspberry Pi devices. This project combines environmental sensors, audio/video streaming capabilities, and a RESTful API to create a comprehensive monitoring solution for baby rooms.

## Features
- **Environmental Monitoring**: Real-time tracking of CO2 levels, temperature, and humidity
- **Power Management**: UPS status monitoring (voltage, current, power, and charge percentage)
- **Video Streaming**: Live video feed with night mode capability via WebRTC
- **LED Control**: Remote control of IR LEDs
- **Audio Streaming**: Two-way audio communication
- **Music Player**: Integrated MP3 player
- **Secure API**: JWT authentication for all endpoints
- **Data Storage**: Time-series data storage using InfluxDB



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


