import asyncio
import cv2
from picamera2 import Picamera2

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.signaling import TcpSocketSignaling
from av import VideoFrame
import fractions
from datetime import datetime

class CustomVideoStreamTrack(VideoStreamTrack):
    def __init__(self, camera_id):
        super().__init__()
        
        self.picam2 = Picamera2()
        #self.picam2.preview_configuration.main.size = (800,800) #(1366,768) #(1920,1080)
        #self.picam2.preview_configuration.main.format = "BGR888"
        #self.picam2.preview_configuration.align()
        #self.picam2.configure("preview")
        #config = self.picam2.create_preview_configuration()
        self.picam2.configure("preview")
        self.picam2.start()

        self.frame_count = 0

    async def recv(self):
        self.frame_count += 1
        print(f"Sending frame {self.frame_count}")
        
        frame = self.picam2.capture_array()

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base
        # Add timestamp to the frame
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Current time with milliseconds
        cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    
        #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, 30)  # Use fractions for time_base
        return video_frame

async def setup_webrtc_and_run(ip_address, port, camera_id):
    signaling = TcpSocketSignaling(ip_address, port)
    pc = RTCPeerConnection()
    video_sender = CustomVideoStreamTrack(camera_id)
    pc.addTrack(video_sender)

    try:
        await signaling.connect()

        @pc.on("datachannel")
        def on_datachannel(channel):
            print(f"Data channel established: {channel.label}")

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state is {pc.connectionState}")
            if pc.connectionState == "connected":
                print("WebRTC connection established successfully")

        offer = await pc.createOffer()
        print("Offer:")
        print(offer)
        await pc.setLocalDescription(offer)
        await signaling.send(pc.localDescription)

        while True:
            obj = await signaling.receive()
            print()
            print(obj)
            print()
            if isinstance(obj, RTCSessionDescription):
                await pc.setRemoteDescription(obj)
                print("Remote description set")
            elif obj is None:
                print("Signaling ended")
                break
        print("Closing connection")
    finally:
        await pc.close()

async def main():
    ip_address = "192.168.4.40" # Ip Address of Remote Server/Machine
    port = 9999
    camera_id = 0  # Change this to the appropriate camera ID
    await setup_webrtc_and_run(ip_address, port, camera_id)

if __name__ == "__main__":
    asyncio.run(main())
