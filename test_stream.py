import urllib.request
import cv2
import numpy as np

try:
    print("Connecting to http://10.26.35.22/ ...")
    stream = urllib.request.urlopen("http://10.26.35.22/", timeout=5)
    bytes_data = b''
    success = False
    for i in range(100):
        chunk = stream.read(2048)
        bytes_data += chunk
        a = bytes_data.find(b'\xff\xd8')
        b = bytes_data.find(b'\xff\xd9')
        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                print(f"SUCCESS! Decoded Frame #{i+1}: {frame.shape}")
                success = True
                break
    if not success:
        print("Failed to decode frame from chunks")
except Exception as e:
    print(f"Stream error: {e}")
