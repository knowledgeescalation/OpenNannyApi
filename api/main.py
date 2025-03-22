from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status, WebSocket, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import jwt
from jwt.exceptions import InvalidTokenError

from passlib.context import CryptContext
from pydantic import BaseModel

import json
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, MediaStreamTrack
from aiortc.mediastreams import MediaStreamError
from starlette.websockets import WebSocketDisconnect

from av import VideoFrame
from picamera2 import Picamera2
import cv2
import fractions

from av import AudioFrame
import pyaudio
import asyncio
import numpy as np

from sensors import get_last
from led_control import right_on, right_off, left_on, left_off

import pygame as pg
from mutagen.mp3 import MP3

import os

from dotenv import load_dotenv

load_dotenv()

start_volume = 0.05
freq = 44100    # audio CD quality
bitsize = -16   # unsigned 16 bit
channels = 2    # 1 is mono, 2 is stereo
buffer = 2048   # number of samples (experiment to get right sound)
pg.mixer.init(freq, bitsize, channels, buffer)
pg.mixer.music.set_volume(start_volume)

picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)  #(1280,720) #(480,640)
picam2.configure("preview")
picam2.start()

camera_night = False

mp3Player = {"song": "", "directory": "", "duration": "", "startPos": 0}

class CustomVideoStreamTrack(VideoStreamTrack):
    def __init__(self, camera):
        super().__init__()

        self.picam2 = camera
        #self.picam2.preview_configuration.main.size = (800,800) #(1366,768) #(1920,1080)
        #self.picam2.preview_configuration.main.format = "BGR888"
        #self.picam2.preview_configuration.align()
        #self.picam2.configure("preview")
        #config = self.picam2.create_preview_configuration()

        self.frame_count = 0

    async def recv(self):

        global camera_night

        self.frame_count += 1
        #print(f"Sending frame {self.frame_count}")

        frame = self.picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base
        # Add timestamp to the frame
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Current time with milliseconds
        cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
       
        if camera_night:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base
        return video_frame



class CustomAudioStreamTrack(MediaStreamTrack):
    """
    A custom audio track that captures audio from a microphone on Raspberry Pi.
    """
    kind = "audio"  # This specifies that this is an audio track

    def __init__(self, device_index=None):
        super().__init__()  # Initialize the parent class
        
        # Initialize PyAudio for microphone capture
        self.audio = pyaudio.PyAudio()
        
        # Configure audio parameters - WebRTC commonly uses these values
        self.channels = 2  # Mono audio (WebRTC typically uses mono)
        self.sample_rate = 48000  # Sample rate in Hz (standard for WebRTC)
        self.chunk_size = 960  # 20ms of audio at 48kHz
        self.format = pyaudio.paInt16  # 16-bit audio
        
        # Find the microphone device index if not provided
        self.device_index = device_index if device_index is not None else self._get_mic_device_index()
        
        if self.device_index is None:
            print("Error: No suitable microphone found. Please check your connections.")
            sys.exit(1)
            
        print(f"Using microphone device index: {self.device_index}")
        
        # Create audio queue for buffer management
        self.audio_queue = asyncio.Queue(maxsize=100)
        
        # Open audio stream
        try:
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.stream.start_stream()
            print("Microphone stream started successfully")
        except Exception as e:
            print(f"Error opening microphone stream: {e}")
            sys.exit(1)
            
        self.frame_count = 0
        self._running = True

    def _get_mic_device_index(self):
        """Find the device index of the microphone"""
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        print("Available audio input devices:")
        usb_mics = []
        
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                name = device_info.get('name')
                print(f"  {i}: {name}")
                
                # Prefer USB microphones
                if 'usb' in name.lower() or 'mic' in name.lower():
                    usb_mics.append(i)
        
        # Return first USB mic if found, otherwise first input device
        if usb_mics:
            return usb_mics[0]
        elif num_devices > 0:
            for i in range(num_devices):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info.get('maxInputChannels') > 0:
                    return i
        
        return None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream - puts audio data in the queue"""
        if status:
            print(f"Audio status: {status}")
        
        if self._running:
            try:
                self.audio_queue.put_nowait(in_data)
            except asyncio.QueueFull:
                pass
                #print("Warning: Audio queue full, dropping frame")
        
        return (None, pyaudio.paContinue)

    async def recv(self):
        """
        Receive the next audio frame.
        This method is called by aiortc to get audio frames.
        """

        #print("Audio RECV")
        if not self._running:
            raise MediaStreamError("Audio track has ended")
            
        self.frame_count += 1
        #print(self.frame_count)
        
        try:
            # Get audio data from the queue with timeout
            audio_data = await asyncio.wait_for(self.audio_queue.get(), timeout=1.0)
            
            # Convert audio data to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)*10
            
            # Create audio frame
            frame = AudioFrame(
                format="s16",  # Signed 16-bit
                layout="mono" if self.channels == 1 else "stereo",
                samples=len(audio_array) // self.channels
            )
            
            # Set the frame data
            frame.planes[0].update(audio_array.tobytes())
            
            # Set time info
            frame.pts = self.frame_count * self.chunk_size
            frame.sample_rate = self.sample_rate
            frame.time_base = fractions.Fraction(1, self.sample_rate)

            #print("Audio frame:", frame)
            
            return frame
            
        except asyncio.TimeoutError:
            # If timeout occurs, create a silent frame
            print("Warning: Audio queue timeout, generating silent frame")
            silent_array = np.zeros(self.chunk_size, dtype=np.int16)
            
            frame = AudioFrame(
                format="s16",
                layout="mono" if self.channels == 1 else "stereo",
                samples=self.chunk_size
            )
            
            frame.planes[0].update(silent_array.tobytes())
            frame.pts = self.frame_count * self.chunk_size
            frame.sample_rate = self.sample_rate
            frame.time_base = fractions.Fraction(1, self.sample_rate)
            
            return frame

        except Exception as e:
            print(e)

    def stop(self):
        """Stop and clean up audio resources"""
        self._running = False
        
        if hasattr(self, 'stream') and self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
        
        print("Audio resources released")


class WebRTCServer:
    def __init__(self):
        self.connections = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
        print("Client connected")
    
    async def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)
        print("Client disconnected")
    
    async def broadcast(self, message: str):
        to_remove = set()
        for connection in self.connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message: {e}")
                to_remove.add(connection)
        for conn in to_remove:
            self.connections.remove(conn)

class MusicItem(BaseModel):
    cmd: str
    parameters: str = None

class LedItem(BaseModel):
    cmd: str

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# htpasswd -bnBC 12 "" secret
users_db = {
    os.getenv('USER_NAME'): {
        "username": os.getenv('USER_NAME'),
        "full_name": os.getenv('FULL_USER_NAME'),
        "email": os.getenv('USER_EMAIL'),
        "hashed_password": os.getenv('USER_HASH'),
        "disabled": False,
    }
}


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None

class UserInDB(User):
    hashed_password: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

webrtc_server = WebRTCServer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)

def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user



async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/token")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],) -> Token:
    user = authenticate_user(users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/user")
async def read_user(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

@app.get("/sensors")
async def info(current_user: Annotated[User, Depends(get_current_active_user)]):
    return get_last()

@app.post("/led")
async def led_post(item: LedItem, current_user: Annotated[User, Depends(get_current_active_user)]):

    global camera_night

    if item.cmd == 'status':
        if camera_night:
            return {'status': 'night'}
        else:
            return {'status': 'day'}
    elif item.cmd == 'night':
        if not camera_night:
            right_on()
            left_on()
            camera_night = True
            return {'status': 'OK'}
        else:
            return {'status': 'Already OK'}
    elif item.cmd == 'day':
        if camera_night:
            right_off()
            left_off()
            camera_night = False
            return {'status': 'OK'}
        else:
            return {'status': 'Already OK'}
    else:
        return {'status': 'Wrong request to API'}

@app.post("/music")
async def music_post(item: MusicItem):#, current_user: Annotated[User, Depends(get_current_active_user)]):

    path = os.getenv('MUSIC_PATH')

    if item.cmd == 'lsdir':
        dirs_json = []
        for d in os.listdir(path):
            if os.path.isdir(os.path.join(path, d)) and d != 'env':
                dirs_json.append({'dir': d})

        return dirs_json

    elif item.cmd == 'lsmp3':
        path = path + '/' + item.parameters
        mp3_json = []
        for f in os.listdir(path):
            if f.endswith(".mp3") and os.path.isfile(os.path.join(path, f)):
                mp3_json.append({'file': f[:-4]})

        return mp3_json


    elif item.cmd == 'play':
        
        music_dir = path + '/' + item.parameters
        if not os.path.exists(music_dir):
            return {"status": f"File not found: {item.parameters}"}

        try:
            music_dir = path + '/' + item.parameters
            pg.mixer.music.load(music_dir)
            directory, song = item.parameters.split('/')
            audio = MP3(music_dir)
            duration = int(audio.info.length)
        except Exception as e:
            return {"status": e}
        finally:
            pg.mixer.music.play()
            mp3Player["song"] = song
            mp3Player["directory"] = directory
            mp3Player["duration"] = duration
            mp3Player["startPos"] = 0
            return {"status": "OK", "duration": duration, "volume": start_volume}


    elif item.cmd == 'pause':
        pg.mixer.music.pause()
    elif item.cmd == 'unpause':
        pg.mixer.music.unpause()
    elif item.cmd == 'stop':
        pg.mixer.music.stop()
        mp3Player['song'] = ""
        mp3Player['directory'] = ""
        mp3Player['duration'] = 0
        mp3Player['startPos'] = 0
    elif item.cmd == 'status':
        if pg.mixer.music.get_busy() or mp3Player["song"] != "":
            currentProgress = int(pg.mixer.music.get_pos()/1000) + mp3Player["startPos"] 
            volume = pg.mixer.music.get_volume()
            if pg.mixer.music.get_busy():
                status = "playing"
            else:
                status = "paused"
            return {
                    "status": status, 
                    "song": mp3Player['song'], 
                    "directory": mp3Player['directory'],
                    "duration": mp3Player['duration'],
                    "currentProgress": currentProgress,
                    "volume": volume
                }
        else:
            return {"status": "stopped"}
    elif item.cmd == 'set_volume':
        try:
            volume = float(item.parameters)
        except ValueError:
            return {"status": "Volume argument invalid. Please use a float (0.0 - 1.0)"}
        pg.mixer.music.set_volume(volume)
    elif item.cmd == 'rewind':
        try:
            new_pos = float(item.parameters)
            mp3Player['startPos'] = int(new_pos)
        except Exception as e:
            return {"status": e}
        finally:
            pg.mixer.music.play()
            pg.mixer.music.set_pos(new_pos)


    return {"status": "OK"}

@app.websocket("/webrtc")
async def websocket_endpoint(websocket: WebSocket, authorization: str = Header(None)):

    if not authorization or not authorization.startswith("Bearer "):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
   
    token = authorization.split("Bearer ")[1]

    print("token:", token)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception as e:
        print('Exception:', e)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await webrtc_server.connect(websocket)
    pc = RTCPeerConnection()
    video_sender = CustomVideoStreamTrack(picam2)
    audio_sender = CustomAudioStreamTrack(0)

    pc.addTrack(video_sender)
    pc.addTrack(audio_sender)

    try:

        @pc.on("datachannel")
        def on_datachannel(channel):
            print(f"Data channel established: {channel.label}")

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "connected":
                print("WebRTC connection established successfully")
            elif pc.connectionState in ["failed", "closed"]:
                print("WebRTC connection failed or closed")
                audio_sender.stop() 

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        await websocket.send_json({"type": pc.localDescription.type, "sdp": pc.localDescription.sdp})

        answer_sdp = await websocket.receive_text()
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await pc.setRemoteDescription(answer)

        while True:
            print("While loop")
            obj = await websocket.receive_text()

            print(obj)

            if obj is None:
                print("Serv end")
                break
        print("Closing connection")

    except WebSocketDisconnect:
        await webrtc_server.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await webrtc_server.disconnect(websocket)

    finally:
        await pc.close()
        audio_sender.stop()
        print("Closing WebRTC")
