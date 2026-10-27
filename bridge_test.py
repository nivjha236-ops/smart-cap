"""
============================================================
  SMART CAP - LIVE BRIDGE TESTER (Test Everything Live)
============================================================
Yeh script:
1. Aapke Camera (ESP32-CAM ya Laptop Webcam) se frame legi.
2. Render Server (https://smartcap-ai.onrender.com) par bhejegi.
3. Server se jaise hi alert aayega, Main ESP32 (10.26.35.113) par
   audio trigger bhej degi taaki DFPlayer turant bol pade!
"""

import cv2
import requests
import time
import urllib.request
import numpy as np

RENDER_URL = "https://smartcap-ai.onrender.com/api/detect"
MAIN_ESP32 = "http://10.26.35.113"
CAMERA_STREAM_URL = "http://10.26.35.22/"

print("="*60)
print("  SMART CAP - TESTING LIVE CLOUD AI & AUDIO VOICE")
print("="*60)

# Check Main ESP32 first
print("\n1. Testing Main ESP32 Audio Board (10.26.35.113)...")
try:
    r = requests.get(f"{MAIN_ESP32}/person?name=unknown", timeout=3)
    print(f"🔊 Audio Test Sent! Status: {r.status_code} (Speaker ne aawaz di?)")
except Exception as e:
    print(f"⚠️ Main ESP32 se contact nahi hua: {e}")

# Check Camera
print("\n2. Connecting to Camera...")
cap = None
use_stream = False

try:
    stream = urllib.request.urlopen(CAMERA_STREAM_URL, timeout=3)
    print("✅ Connected to ESP32-CAM Stream (10.26.35.22)!")
    use_stream = True
except Exception as e:
    print(f"⚠️ ESP32-CAM (10.26.35.22) offline ya IP badal gaya hai ({e}).")
    print("👉 Fallback: Laptop ke Webcam se test kar rahe hain...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Koi camera nahi mila. Kripya ESP32-CAM ka IP check karein.")

bytes_data = b''
print("\n🚀 Starting Live AI Loop to Render Cloud...")
print("Samne kisi aadmi ko laiye ya camera ke aage aaiye. Press Ctrl+C to stop.\n")

last_trigger = 0

try:
    while True:
        frame = None
        if use_stream:
            try:
                bytes_data += stream.read(2048)
                a = bytes_data.find(b'\xff\xd8')
                b = bytes_data.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = bytes_data[a:b+2]
                    bytes_data = bytes_data[b+2:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception as e:
                time.sleep(0.5)
                try:
                    stream = urllib.request.urlopen(CAMERA_STREAM_URL, timeout=3)
                except:
                    pass
                continue
        elif cap is not None:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.2)
                continue

        if frame is None:
            time.sleep(0.1)
            continue

        # Resize for fast 4G / Cloud upload
        small = cv2.resize(frame, (320, 240))
        _, jpg_buf = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 70])

        try:
            # Send to Render Cloud
            res = requests.post(
                RENDER_URL,
                data=jpg_buf.tobytes(),
                headers={"Content-Type": "image/jpeg"},
                timeout=5
            )
            data = res.json()
            detections = data.get("detections", [])
            alert = data.get("alert")
            alert_msg = data.get("alert_message")

            print(f"👁️ Render AI Dekh Raha Hai: {detections} | Alert: {alert_msg}")

            # Agar alert trigger hua hai toh Main ESP32 par voice bajao
            if alert and (time.time() - last_trigger > 3.0):
                last_trigger = time.time()
                url = f"{MAIN_ESP32}/{alert}"
                print(f"🔊 [TRIGGERING DFPLAYER] -> {url} ({alert_msg})")
                try:
                    requests.get(url, timeout=1.5)
                except:
                    pass

        except Exception as e:
            print(f"Cloud upload error: {e}")

        time.sleep(0.4) # ~2 frames per second

except KeyboardInterrupt:
    print("\nStopped.")
    if cap: cap.release()
