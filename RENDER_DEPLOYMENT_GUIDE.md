# 🧢 Smart Cap AI - Render Cloud Hosting Guide (GP Siwan / Bihar Talent)

Yeh guide aapko batayegi ki kaise aap apne Smart Cap AI server ko **Render.com** par bilkul free me host kar sakte hain, taaki aapko apna laptop hamesha sath lekar na ghumna pade aur sirf mobile hotspot on karte hi cap apne aap kaam karne lage.

---

## 🧠 1. Problem aur Solution Samajhiye (Architecture)

### Pehle Kya Ho Raha Tha (Laptop Dependent):
```
[ESP32-CAM (10.26.35.22)] ---> (Stream) ---> [Laptop (run_ai.py)] ---> [Main ESP32 (10.26.35.113)]
```
- Isme aapka laptop dono boards ke beech me tha.
- Dono IP (`10.26.35.x`) aapke local hotspot ke the, isliye Render par direct connect nahi ho sakte the.

### Ab Naya Cloud System (100% Free from Laptop):
```
1. [ESP32-CAM] ---> (Photo Upload over 4G Hotspot) ---> [Render Cloud Server (app.py)]
                                                                    |
                                                            (AI Analysis: YOLOv8 + Face)
                                                                    |
2. [ESP32-CAM] <--- (Alert Result: "dog", "fire", etc.) <-----------|
       |
3. (Local Hotspot Call)
       v
[Main ESP32 (DFPlayer Mini)] ---> 🔊 "Kutta Samne Hai!" / "Aag Samne Hai!"
```
**Sabse bada faayda:**
1. **Laptop ki zaroorat khatam!**
2. **Main ESP32 me koi change nahi karna padega!**
3. **Live Dashboard:** Exhibition ya presentation ke time koi bhi teacher ya judge apne phone me aapka Render URL khol kar live camera aur bounding boxes dekh sakta hai!

---

## 🚀 2. Render Par Deploy Karne Ke Steps (Step-by-Step)

### Step 1: GitHub Par Code Daalna
Render direct GitHub se code uthata hai.
1. [GitHub.com](https://github.com) par login karke ek New Repository banayein (naam rakhein: `SmartCapAI`).
2. Is repository me ye zaroori files upload kar dijiye:
   - `app.py`
   - `requirements.txt`
   - `Procfile`
   - `render.yaml`
   - `yolov8n.onnx`
   - `haarcascade_frontalface_default.xml`
   - `shridev.jpg`

*(Agar Git command use karte hain:)*
```bash
cd "c:\Users\HP\Desktop\New folder\SmartCapAI"
git init
git add app.py requirements.txt Procfile render.yaml yolov8n.onnx haarcascade_frontalface_default.xml shridev.jpg
git commit -m "Initial SmartCap Cloud Setup"
git branch -M main
git remote add origin https://github.com/AAPKA_USERNAME/SmartCapAI.git
git push -u origin main
```

---

### Step 2: Render.com Par Web Service Banana
1. [Render.com](https://render.com) par jaakar free account banayein ya GitHub se Login karein.
2. Dashboard par **New +** button par click karke **Web Service** chunein.
3. Apni GitHub repository (`SmartCapAI`) ko select karke **Connect** par click karein.
4. Settings me ye daalein:
   - **Name:** `smartcap-ai` (ya jo aap chahein)
   - **Region:** `Singapore` (India ke sabse paas hai, fast speed milegi)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
   - **Instance Type:** `Free` (512 MB RAM)
5. **Environment Variables** (Neeche scroll karein):
   - Key: `PYTHON_VERSION`
   - Value: `3.11.8`
6. Click karein **Deploy Web Service**!

Thodi der me (2-3 minute) me build complete ho jayega aur aapko apna Live URL mil jayega, jaise:
`https://smartcap-ai.onrender.com`

---

### Step 3: Render Ko 24/7 Awake Rakhna (Sleep Hone Se Bachana)
Render Free Tier 15 minute baad sleep mode me chala jata hai. Isko hamesha active rakhne ke liye:
1. Free website [cron-job.org](https://cron-job.org) ya [uptimerobot.com](https://uptimerobot.com) par free account banayein.
2. Ek naya monitor/cron job banayein:
   - URL: `https://your-app-name.onrender.com/health`
   - Interval: Every `10 minutes`
3. Ab aapka server kabhi sleep nahi hoga aur 24x7 bina delay ke kaam karega!

---

## 🧢 3. ESP32-CAM Setup (Smart Cap Par Flash Karna)

Folder ke andar:
`esp32_code/ESP32_CAM_SmartCap/ESP32_CAM_SmartCap.ino`

1. Is file ko **Arduino IDE** me open karein.
2. Upar ye 3 settings change karein:
   ```cpp
   // 1. Apna Mobile Hotspot ka naam aur password:
   const char* ssid     = "APNA_HOTSPOT_NAME";
   const char* password = "APNA_PASSWORD";

   // 2. Render se jo URL mila (bina https:// ke):
   const char* RENDER_HOST = "smartcap-ai.onrender.com";

   // 3. DFPlayer wale Main ESP32 ka IP:
   const char* MAIN_ESP32_IP = "10.26.35.113";
   ```
3. Board select karein: `AI Thinker ESP32-CAM`.
4. Upload par click karke flash kar dein!

---

## 📱 4. Kaise Chalayein (Exhibition / Real World)

1. Apne phone ka **Hotspot** on kijiye (Same SSID aur Password jo code me dala tha).
2. Smart Cap ka power switch ON kijiye (Power Bank se).
3. ESP32-CAM turant phone ke hotspot se connect hoga aur photos Render Cloud par bhejne lagega.
4. Render Cloud AI se detect karega (Kutta, Gadi, Aag, Shridev Bhaiya, etc.) aur Main ESP32 ko DFPlayer se voice alert bolne ka signal de dega!
5. Agar phone me dekhna ho: Kisi bhi phone ke browser me apna URL (`https://smartcap-ai.onrender.com`) khol lijiye — wahan live video aur bounding boxes dikhayi denge!
