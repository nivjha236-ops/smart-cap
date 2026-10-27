import os
import time
import cv2
import numpy as np
from flask import Flask, request, jsonify, Response, render_template_string

app = Flask(__name__)

# ==================== CONFIGURATION ====================
CONFIDENCE_THRESHOLD = 0.45
NMS_THRESHOLD = 0.50
ALERT_COOLDOWN = 3.5 # Seconds

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
print("="*65)
print("  SMART CAP - MASTER AI VISION ENGINE (RENDER CLOUD)")
print("="*65)
print("[AI] Loading YOLOv8 Neural Network into OpenCV...")
model_path = os.path.join(os.path.dirname(__file__), "yolov8n.onnx")
net = cv2.dnn.readNet(model_path)
try:
    if hasattr(cv2.dnn, 'DNN_BACKEND_OPENCV'):
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    if hasattr(cv2.dnn, 'DNN_TARGET_CPU'):
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
except Exception:
    pass
print("[AI] Neural Network Loaded Successfully!")

# Load Haar Face Detector (Resilient to OpenCV 4 and 5)
face_cascade = None
cascade_file = os.path.join(os.path.dirname(__file__), "haarcascade_frontalface_default.xml")
if not os.path.exists(cascade_file) and hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
    cascade_file = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

try:
    if hasattr(cv2, 'CascadeClassifier'):
        face_cascade = cv2.CascadeClassifier(cascade_file)
        print("✅ [AI] CascadeClassifier initialized from cv2!")
    elif hasattr(cv2, 'objdetect') and hasattr(cv2.objdetect, 'CascadeClassifier'):
        face_cascade = cv2.objdetect.CascadeClassifier(cascade_file)
        print("✅ [AI] CascadeClassifier initialized from cv2.objdetect!")
    else:
        print("⚠️ [INFO] CascadeClassifier not found in current OpenCV build. Using YOLO-based face ROI fallback.")
except Exception as e:
    print(f"⚠️ [WARNING] Could not load face cascade: {e}")

# Load Shridev Bhaiya's Face Profile
shridev_hist = None
shridev_path = os.path.join(os.path.dirname(__file__), "shridev.jpg")
try:
    if os.path.exists(shridev_path):
        ref_img = cv2.imread(shridev_path)
        if ref_img is not None:
            ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
            face_roi = None
            if face_cascade is not None:
                ref_faces = face_cascade.detectMultiScale(ref_gray, 1.1, 4)
                if len(ref_faces) > 0:
                    rx, ry, rw, rh = ref_faces[0]
                    face_roi = ref_gray[ry:ry+rh, rx:rx+rw]
            
            # If no cascade or face not detected, use upper-center portion as face profile
            if face_roi is None:
                rh, rw = ref_gray.shape
                face_roi = ref_gray[int(rh*0.1):int(rh*0.6), int(rw*0.2):int(rw*0.8)]

            shridev_hist = cv2.calcHist([face_roi], [0], None, [256], [0, 256])
            cv2.normalize(shridev_hist, shridev_hist, 0, 1, cv2.NORM_MINMAX)
            print("👑 [SUCCESS] Shridev Bhaiya's Profile Loaded & Calibrated!")
except Exception as e:
    print(f"[WARNING] Could not load shridev.jpg: {e}")

# Global state for dashboard and live stream
last_trigger_time = 0
last_alert = {
    "type": "none",
    "endpoint": "",
    "message": "System Ready",
    "timestamp": time.time(),
    "alert_id": 0
}
alert_counter = 0
latest_annotated_jpeg = None
total_frames_processed = 0

def detect_fire(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_fire = np.array([15, 120, 180])
    upper_fire = np.array([35, 255, 255])
    mask = cv2.inRange(hsv, lower_fire, upper_fire)
    fire_pixels = cv2.countNonZero(mask)
    return fire_pixels > 1200

def run_yolo_detection(frame):
    h, w, _ = frame.shape
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
        if max_score >= CONFIDENCE_THRESHOLD:
            class_id = np.argmax(classes_scores)
            cx, cy, bw, bh = row[0], row[1], row[2], row[3]
            left = int((cx - 0.5 * bw) * x_factor)
            top  = int((cy - 0.5 * bh) * y_factor)
            width = int(bw * x_factor)
            height = int(bh * y_factor)
            boxes.append([left, top, width, height])
            confidences.append(float(max_score))
            class_ids.append(class_id)

    indices = cv2.dnn.NMSBoxes(boxes, confidences, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
    results = []
    if len(indices) > 0:
        for i in indices.flatten():
            results.append((CLASSES[class_ids[i]], confidences[i], boxes[i]))
    return results

def process_frame(frame):
    global last_trigger_time, last_alert, alert_counter, latest_annotated_jpeg, total_frames_processed
    total_frames_processed += 1
    
    small_frame = cv2.resize(frame, (480, 360))
    h, w, _ = small_frame.shape

    alert_endpoint = None
    alert_type = None
    alert_message = None

    # 1. Fire / Flame Check
    is_fire = detect_fire(small_frame)
    if is_fire:
        cv2.putText(small_frame, "FIRE DETECTED!", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        alert_endpoint = "hazard?type=fire"
        alert_type = "fire"
        alert_message = "Aag (Fire) Samne Hai!"

    # 2. YOLO Object Detection
    detections = run_yolo_detection(small_frame)
    detected_labels = [d[0] for d in detections]
    person_boxes = []

    for label, conf, box in detections:
        x, y, bw, bh = box
        color = (0, 255, 0)
        if label in ['dog', 'cow']: color = (255, 165, 0)
        elif label in ['car', 'motorcycle', 'truck', 'bus']: color = (0, 140, 255)
        
        cv2.rectangle(small_frame, (x, y), (x + bw, y + bh), color, 2)
        cv2.putText(small_frame, f"{label} {int(conf*100)}%", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

        if label == 'person':
            person_boxes.append(box)

        # Low Obstacle / Pole Check
        if (y + bh) > (h * 0.72) and label in ['chair', 'bench', 'fire hydrant', 'potted plant', 'traffic light']:
            cv2.putText(small_frame, "LOW POLE / OBSTACLE!", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            if not alert_endpoint:
                alert_endpoint = "hazard?type=pole"
                alert_type = "pole"
                alert_message = "Kamba / Rukawat Samne Hai!"

    # 3. Decision Logic Triggers (Priority Order)
    if not alert_endpoint:
        if 'dog' in detected_labels:
            alert_endpoint = "animal?type=dog"
            alert_type = "dog"
            alert_message = "Kutta (Dog) Samne Hai!"
        elif 'cow' in detected_labels or 'sheep' in detected_labels or 'horse' in detected_labels:
            alert_endpoint = "animal?type=cow"
            alert_type = "cow"
            alert_message = "Janwar (Cow) Samne Hai!"
        elif 'car' in detected_labels or 'truck' in detected_labels or 'bus' in detected_labels:
            alert_endpoint = "hazard?type=car"
            alert_type = "car"
            alert_message = "Gadi (Car) Samne Hai!"
        elif 'motorcycle' in detected_labels or 'bicycle' in detected_labels:
            alert_endpoint = "hazard?type=bike"
            alert_type = "bike"
            alert_message = "Bike Samne Hai!"
        elif 'person' in detected_labels:
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            is_shridev = False

            # Try cascade detection first if available
            if face_cascade is not None:
                faces = face_cascade.detectMultiScale(gray, 1.2, 4)
                if len(faces) > 0 and shridev_hist is not None:
                    fx, fy, fw, fh = faces[0]
                    current_face = gray[fy:fy+fh, fx:fx+fw]
                    curr_hist = cv2.calcHist([current_face], [0], None, [256], [0, 256])
                    cv2.normalize(curr_hist, curr_hist, 0, 1, cv2.NORM_MINMAX)
                    similarity = cv2.compareHist(shridev_hist, curr_hist, cv2.HISTCMP_CORREL)
                    if similarity > 0.55:
                        is_shridev = True
            elif len(person_boxes) > 0 and shridev_hist is not None:
                # Fallback: check upper 35% of person bounding box
                px, py, pw, ph = person_boxes[0]
                face_y1 = max(0, py)
                face_y2 = min(h, py + int(ph * 0.35))
                face_x1 = max(0, px)
                face_x2 = min(w, px + pw)
                if face_y2 > face_y1 and face_x2 > face_x1:
                    current_face = gray[face_y1:face_y2, face_x1:face_x2]
                    curr_hist = cv2.calcHist([current_face], [0], None, [256], [0, 256])
                    cv2.normalize(curr_hist, curr_hist, 0, 1, cv2.NORM_MINMAX)
                    similarity = cv2.compareHist(shridev_hist, curr_hist, cv2.HISTCMP_CORREL)
                    if similarity > 0.55:
                        is_shridev = True

            if is_shridev:
                cv2.putText(small_frame, "SHRIDEV BHAIYA", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                alert_endpoint = "person?name=shridev"
                alert_type = "shridev"
                alert_message = "Shridev Bhaiya Samne Hain!"
            else:
                cv2.putText(small_frame, "UNKNOWN PERSON", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                alert_endpoint = "person?name=unknown"
                alert_type = "unknown_person"
                alert_message = "Koi Vyakti Samne Hai!"

    # Handle Cooldown
    now = time.time()
    triggered = False
    if alert_endpoint and (now - last_trigger_time > ALERT_COOLDOWN):
        last_trigger_time = now
        alert_counter += 1
        last_alert = {
            "type": alert_type,
            "endpoint": alert_endpoint,
            "message": alert_message,
            "timestamp": now,
            "alert_id": alert_counter
        }
        triggered = True
        print(f"🔊 [CLOUD ALERT TRIGGERED #{alert_counter}] -> {alert_endpoint} ({alert_message})")

    # Encode annotated frame for web streaming
    _, buffer = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    latest_annotated_jpeg = buffer.tobytes()

    return {
        "status": "success",
        "detections": detected_labels,
        "fire": is_fire,
        "alert": alert_endpoint if triggered else None,
        "alert_type": alert_type if triggered else None,
        "alert_message": alert_message if triggered else None,
        "triggered": triggered,
        "alert_id": alert_counter
    }

# ==================== API ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "SmartCap AI Cloud Engine",
        "uptime_now": time.time(),
        "total_frames": total_frames_processed
    })

@app.route('/api/detect', methods=['POST'])
@app.route('/detect', methods=['POST'])
def detect():
    """
    Main Endpoint for ESP32-CAM or Client App:
    Accepts raw binary image (image/jpeg) or multipart form-data ('image' / 'frame').
    """
    frame = None

    if 'image' in request.files:
        file = request.files['image']
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    elif 'frame' in request.files:
        file = request.files['frame']
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    elif request.data:
        file_bytes = np.frombuffer(request.data, np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"status": "error", "message": "No valid JPEG image received"}), 400

    result = process_frame(frame)
    return jsonify(result)

@app.route('/api/latest-alert', methods=['GET'])
@app.route('/alert', methods=['GET'])
def get_latest_alert():
    return jsonify(last_alert)

# ==================== WEB DASHBOARD & STREAM ====================

def gen_frames():
    global latest_annotated_jpeg
    while True:
        if latest_annotated_jpeg is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_annotated_jpeg + b'\r\n')
        time.sleep(0.08)

@app.route('/stream')
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def dashboard():
    html_template = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Cap AI - Cloud Vision Engine</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background: #0f172a; color: #f8fafc; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        header { text-align: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 28px; margin-bottom: 5px; }
        .subtitle { color: #94a3b8; font-size: 14px; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-top: 8px; }
        .badge-live { background: #16a34a; color: #fff; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
        .card { background: #1e293b; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); border: 1px solid #334155; }
        .card h2 { font-size: 18px; margin-bottom: 15px; color: #cbd5e1; display: flex; align-items: center; gap: 8px; }
        .stream-box { width: 100%; aspect-ratio: 4/3; background: #020617; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 2px dashed #475569; position: relative; }
        .stream-box img { width: 100%; height: 100%; object-fit: contain; }
        .stat-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 15px; }
        .stat-item { background: #0f172a; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #334155; }
        .stat-val { font-size: 22px; font-weight: 700; color: #38bdf8; }
        .stat-lbl { font-size: 12px; color: #94a3b8; }
        .alert-banner { background: #451a03; border: 1px solid #f97316; padding: 15px; border-radius: 8px; margin-bottom: 15px; display: flex; align-items: center; gap: 12px; }
        .alert-banner.active { background: #7f1d1d; border-color: #ef4444; animation: pulse 1s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.8; } 100% { opacity: 1; } }
        .alert-text { font-size: 15px; font-weight: 600; color: #fecdd3; }
        .upload-section { margin-top: 15px; padding-top: 15px; border-top: 1px solid #334155; }
        input[type="file"] { display: none; }
        .custom-file-upload { display: block; text-align: center; background: #0284c7; color: white; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 14px; transition: 0.2s; }
        .custom-file-upload:hover { background: #0369a1; }
        .footer { text-align: center; margin-top: 30px; font-size: 13px; color: #64748b; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧢 Smart Cap AI - Cloud Vision Engine</h1>
            <p class="subtitle">Government Polytechnic Siwan | Bihar Talent Hunt | Shridev Bhaiya Team</p>
            <span class="badge badge-live">● CLOUD SERVER ONLINE (RENDER)</span>
        </header>

        <div class="grid">
            <div class="card">
                <h2>📹 Live AI Stream</h2>
                <div class="stream-box">
                    <img id="liveImg" src="/stream" onerror="this.src='data:image/svg+xml,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'400\\' height=\\'300\\'><rect fill=\\'%23020617\\' width=\\'400\\' height=\\'300\\'/><text fill=\\'%2364748b\\' x=\\'50%\\' y=\\'50%\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\'>Waiting for ESP32-CAM Frames...</text></svg>'">
                </div>
                <div class="upload-section">
                    <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">Want to test manually without ESP32? Upload a photo:</p>
                    <label class="custom-file-upload">
                        <input type="file" id="testFileInput" accept="image/*" onchange="uploadTestImage()">
                        📁 Choose Photo to Test AI
                    </label>
                </div>
            </div>

            <div class="card">
                <h2>⚡ Live Stats & Alerts</h2>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-val" id="statFrames">0</div>
                        <div class="stat-lbl">Processed Frames</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-val" id="statAlerts">0</div>
                        <div class="stat-lbl">Voice Alerts Fired</div>
                    </div>
                </div>

                <div class="alert-banner" id="alertBox">
                    <div style="font-size: 28px;">🔊</div>
                    <div>
                        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #fdba74;">Current Audio Alert</div>
                        <div class="alert-text" id="alertMsg">System Listening for Smart Cap...</div>
                    </div>
                </div>

                <h2>📡 API Endpoints for ESP32</h2>
                <div style="background: #0f172a; padding: 12px; border-radius: 8px; font-size: 12px; color: #94a3b8; line-height: 1.6; border: 1px solid #334155;">
                    <div><b>ESP32-CAM Upload:</b> <code>POST /api/detect</code></div>
                    <div><b>ESP32 Master Poll:</b> <code>GET /api/latest-alert</code></div>
                    <div><b>Web Live Stream:</b> <code>GET /stream</code></div>
                </div>
            </div>
        </div>

        <div class="footer">
            Smart Cap AI Project © 2026 | Built for Visual Assistance & Safety
        </div>
    </div>

    <script>
        async function fetchStats() {
            try {
                const res = await fetch('/api/latest-alert');
                const data = await res.json();
                if (data.endpoint) {
                    document.getElementById('alertMsg').innerText = (data.message || data.endpoint) + " (" + data.endpoint + ")";
                    document.getElementById('alertBox').classList.add('active');
                } else {
                    document.getElementById('alertMsg').innerText = "All Clear - No Hazard";
                    document.getElementById('alertBox').classList.remove('active');
                }
                document.getElementById('statAlerts').innerText = data.alert_id || 0;

                const hRes = await fetch('/health');
                const hData = await hRes.json();
                document.getElementById('statFrames').innerText = hData.total_frames || 0;
            } catch(e) {}
        }
        setInterval(fetchStats, 1000);

        async function uploadTestImage() {
            const fileInput = document.getElementById('testFileInput');
            if (!fileInput.files[0]) return;
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);

            const res = await fetch('/api/detect', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            alert("AI Result: " + JSON.stringify(data, null, 2));
            fetchStats();
        }
    </script>
</body>
</html>
    """
    return render_template_string(html_template)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🚀 Smart Cap Cloud AI Server starting on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
