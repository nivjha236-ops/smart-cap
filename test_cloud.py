"""
============================================================
  SMART CAP - CLOUD SERVER TESTER (Python)
============================================================
Yeh script check karegi ki aapka Render Server theek se chal raha hai ya nahi.
"""

import sys
import requests
import cv2
import time

# Apne Render Server ka URL yahan daalein:
SERVER_URL = "http://localhost:5000" # Ya "https://smartcap-ai.onrender.com"

if len(sys.argv) > 1:
    SERVER_URL = sys.argv[1]

print(f"📡 Testing Server: {SERVER_URL}")

# 1. Check Health Endpoint
try:
    r = requests.get(f"{SERVER_URL}/health", timeout=10)
    print("✅ Health Check:", r.json())
except Exception as e:
    print("❌ Server se connect nahi ho paya:", e)
    print("Tip: Pehle 'python app.py' start karein!")
    sys.exit(1)

# 2. Test Image Detection with shridev.jpg
print("\n🔍 Testing Detection Endpoint with shridev.jpg...")
try:
    with open("shridev.jpg", "rb") as f:
        img_bytes = f.read()

    r = requests.post(
        f"{SERVER_URL}/api/detect",
        data=img_bytes,
        headers={"Content-Type": "image/jpeg"},
        timeout=15
    )
    print("✅ Server Response:", r.json())
except Exception as e:
    print("❌ Detection test failed:", e)

# 3. Check Latest Alert
try:
    r = requests.get(f"{SERVER_URL}/api/latest-alert", timeout=5)
    print("\n🔊 Latest Audio Alert:", r.json())
except Exception as e:
    print("❌ Alert check failed:", e)

print("\n🎉 Test Complete! Server is working properly.")
