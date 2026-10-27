import cv2
import numpy as np
import requests
import time
import urllib.request

# ==================== 1. CONFIGURATION ====================
# ESP32-CAM IP (Camera Stream)
CAMERA_STREAM_URL = "http://10.26.35.22/"

# Main ESP32 Board IP (DFPlayer + Sensors)
ESP32_MASTER_URL  = "http://10.26.35.113"
# ==========================================================

print("="*65)
print("  SMART CAP - MASTER AI VISION ENGINE (GP SIWAN / BIHAR TALENT)")
print("="*65)

# 80 COCO Classes for YOLOv8
CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator",
    "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# Load YOLOv8 ONNX Model
print("[AI] Loading YOLOv8 Neural Network into OpenCV...")
net = cv2.dnn.readNet("yolov8n.onnx")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
print("[AI] Neural Network Loaded Successfully!")

# Load Haar Face Detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Load Shridev Bhaiya's Face Profile
shridev_hist = None
try:
    ref_img = cv2.imread("shridev.jpg")
    if ref_img is not None:
        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
        ref_faces = face_cascade.detectMultiScale(ref_gray, 1.1, 4)
        if len(ref_faces) > 0:
            rx, ry, rw, rh = ref_faces[0]
            face_roi = ref_gray[ry:ry+rh, rx:rx+rw]
            shridev_hist = cv2.calcHist([face_roi], [0], None, [256], [0, 256])
            cv2.normalize(shridev_hist, shridev_hist, 0, 1, cv2.NORM_MINMAX)
            print("👑 [SUCCESS] Shridev Bhaiya's Face Profile Loaded & Calibrated!")
        else:
            shridev_hist = cv2.calcHist([ref_gray], [0], None, [256], [0, 256])
            cv2.normalize(shridev_hist, shridev_hist, 0, 1, cv2.NORM_MINMAX)
            print("👑 [INFO] Full Image Profile Loaded for Shridev Bhaiya!")
except Exception as e:
    print(f"[WARNING] Could not load shridev.jpg: {e}")

last_trigger_time = 0

def send_alert(endpoint):
    global last_trigger_time
    now = time.time()
    if now - last_trigger_time > 3.5: # 3.5 seconds cooldown
        try:
            url = f"{ESP32_MASTER_URL}/{endpoint}"
            print(f"🔊 [TRIGGER SENT] -> {url}")
            requests.get(url, timeout=1.2)
            last_trigger_time = now
        except Exception as e:
            pass

def detect_fire(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_fire = np.array([15, 120, 180])
    upper_fire = np.array([35, 255, 255])
    mask = cv2.inRange(hsv, lower_fire, upper_fire)
    fire_pixels = cv2.countNonZero(mask)
    return fire_pixels > 1200

def run_yolo_detection(frame):
    [h, w, _] = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward()

    output = np.squeeze(outputs[0]).T
    boxes = []
    confidences = []
    class_ids = []

    x_factor = w / 640.0
    y_factor = h / 640.0

    for row in output:
        classes_scores = row[4:]
        max_score = np.amax(classes_scores)
        if max_score >= 0.45:
            class_id = np.argmax(classes_scores)
            cx, cy, bw, bh = row[0], row[1], row[2], row[3]
            left = int((cx - 0.5 * bw) * x_factor)
            top  = int((cy - 0.5 * bh) * y_factor)
            width = int(bw * x_factor)
            height = int(bh * y_factor)
            boxes.append([left, top, width, height])
            confidences.append(float(max_score))
            class_ids.append(class_id)

    indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.45, 0.50)
    results = []
    if len(indices) > 0:
        for i in indices.flatten():
            results.append((CLASSES[class_ids[i]], confidences[i], boxes[i]))
    return results

print(f"\n🚀 Connecting to Camera at {CAMERA_STREAM_URL} ...")
print("💡 Tip: Agar phone me camera khula hai to phone ka tab band kar dijiye taaki laptop connect ho sake.\n")

# Use resilient MJPEG stream reader
def get_camera_stream():
    try:
        return urllib.request.urlopen(CAMERA_STREAM_URL, timeout=8)
    except Exception as e:
        print(f"[RETRY] Camera connection: {e}")
        return None

stream = get_camera_stream()
bytes_data = b''

print("✅ AI Vision Engine Active! Press 'q' on video window to stop.\n")

while True:
    if stream is None:
        time.sleep(1)
        stream = get_camera_stream()
        continue

    try:
        bytes_data += stream.read(2048)
        a = bytes_data.find(b'\xff\xd8')
        b = bytes_data.find(b'\xff\xd9')
        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue

            small_frame = cv2.resize(frame, (480, 360))
            h, w, _ = small_frame.shape

            # 1. Fire / Flame Check
            if detect_fire(small_frame):
                cv2.putText(small_frame, "FIRE DETECTED!", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                send_alert("hazard?type=fire")

            # 2. YOLO Object Detection
            detections = run_yolo_detection(small_frame)
            detected_labels = [d[0] for d in detections]

            for label, conf, box in detections:
                x, y, bw, bh = box
                color = (0, 255, 0)
                if label in ['dog', 'cow']: color = (255, 165, 0)
                elif label in ['car', 'motorcycle', 'truck', 'bus']: color = (0, 140, 255)
                
                cv2.rectangle(small_frame, (x, y), (x + bw, y + bh), color, 2)
                cv2.putText(small_frame, f"{label} {int(conf*100)}%", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

                # Low Obstacle / Pole Check
                if (y + bh) > (h * 0.72) and label in ['chair', 'bench', 'fire hydrant', 'potted plant', 'traffic light']:
                    cv2.putText(small_frame, "LOW POLE / OBSTACLE!", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
                    send_alert("hazard?type=pole")

            # 3. Decision Logic Triggers
            if 'dog' in detected_labels:
                send_alert("animal?type=dog")
            elif 'cow' in detected_labels or 'sheep' in detected_labels or 'horse' in detected_labels:
                send_alert("animal?type=cow")
            elif 'car' in detected_labels or 'truck' in detected_labels or 'bus' in detected_labels:
                send_alert("hazard?type=car")
            elif 'motorcycle' in detected_labels or 'bicycle' in detected_labels:
                send_alert("hazard?type=bike")
            elif 'person' in detected_labels:
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.2, 4)
                is_shridev = False

                if len(faces) > 0 and shridev_hist is not None:
                    fx, fy, fw, fh = faces[0]
                    current_face = gray[fy:fy+fh, fx:fx+fw]
                    curr_hist = cv2.calcHist([current_face], [0], None, [256], [0, 256])
                    cv2.normalize(curr_hist, curr_hist, 0, 1, cv2.NORM_MINMAX)

                    similarity = cv2.compareHist(shridev_hist, curr_hist, cv2.HISTCMP_CORREL)
                    if similarity > 0.55:
                        is_shridev = True

                if is_shridev:
                    cv2.putText(small_frame, "SHRIDEV BHAIYA", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    send_alert("person?name=shridev")
                else:
                    cv2.putText(small_frame, "UNKNOWN PERSON", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    send_alert("person?name=unknown")

            cv2.imshow("Smart Cap - Master AI Vision Engine", small_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        print(f"[RECONNECTING] Stream read: {e}")
        try:
            stream.close()
        except:
            pass
        stream = None
        time.sleep(1)

cv2.destroyAllWindows()
