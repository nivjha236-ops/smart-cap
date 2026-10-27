/*
 =========================================================================================
   SMART CAP - ESP32-CAM AI CLIENT (CONNECTS TO RENDER CLOUD)
   GP Siwan / Bihar Talent Hunt
 =========================================================================================
   Description:
   Yeh sketch ESP32-CAM par flash hoga. Yeh camera se photo lega aur Render Server par
   bheje ga (HTTPS POST). Render Server AI se detect karke alert wapas bhejega.
   Jaise hi alert aayega, ESP32-CAM turant aapke Main ESP32 (10.26.35.113) ko trigger karega!

   Faayda:
   1. Laptop ko sath lekar ghumne ki zaroorat nahi hai.
   2. Mobile Hotspot on karte hi yeh internet se connect hokar kaam karne lagega!
   3. Main ESP32 me koi change nahi karna padega!
 =========================================================================================
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

// ==================== 1. WI-FI CREDENTIALS ====================
// Apne Mobile Hotspot ka Naam aur Password yahan daalein:
const char* ssid     = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_HOTSPOT_PASSWORD";

// ==================== 2. RENDER SERVER URL ====================
// Render par deploy karne ke baad jo URL milega, uska domain name yahan daalein:
// (Bina "https://" aur bina aakhiri slash "/" ke):
const char* RENDER_HOST = "smartcap-ai.onrender.com"; 
const int   RENDER_PORT = 443; // HTTPS Port

// ==================== 3. MAIN ESP32 IP ====================
// DFPlayer wale Main ESP32 ka local IP (Hotspot se jo IP milta hai):
const char* MAIN_ESP32_IP = "10.26.35.113";
// ==============================================================

// CAMERA PIN CONFIGURATION (AI THINKER MODEL)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

WiFiClientSecure secureClient;

void setupCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Frame size: QVGA (320x240) ya CIF (400x296) for super fast 4G upload
  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA; // 320x240 (Fast upload over 4G)
    config.jpeg_quality = 12;          // 10-15 best balance
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 15;
    config.fb_count = 1;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("[ERROR] Camera init failed: 0x%x\n", err);
    while (true) delay(1000);
  }
  Serial.println("✅ Camera Initialized Successfully!");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n======================================");
  Serial.println("  SMART CAP - ESP32-CAM CLOUD CLIENT  ");
  Serial.println("======================================");

  setupCamera();

  // Connect to Mobile Hotspot Wi-Fi
  Serial.printf("Connecting to Wi-Fi: %s", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected!");
  Serial.print("ESP32-CAM IP: ");
  Serial.println(WiFi.localIP());

  // Allow HTTPS without checking SSL certificate (Fast & lightweight)
  secureClient.setInsecure();
  secureClient.setTimeout(5); // 5 seconds timeout
}

void sendAlertToMaster(String alertEndpoint) {
  if (alertEndpoint.length() == 0) return;

  Serial.println("🔊 Triggering Main ESP32 locally: " + alertEndpoint);

  // Send local HTTP request to Main ESP32
  HTTPClient localClient;
  String fullUrl = "http://" + String(MAIN_ESP32_IP) + "/" + alertEndpoint;
  localClient.begin(fullUrl);
  localClient.setTimeout(1500);
  int httpCode = localClient.GET();
  if (httpCode > 0) {
    Serial.printf("✅ Main ESP32 Responded: %d\n", httpCode);
  } else {
    Serial.printf("⚠️ Main ESP32 Error: %s\n", localClient.errorToString(httpCode).c_str());
  }
  localClient.end();

  // Also print to Serial (agar TX pin Main ESP32 ke RX se judi ho to Serial se bhi mil jayega)
  Serial.print("ALERT_TRIGGER:");
  Serial.println(alertEndpoint);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi reconnecting...");
    WiFi.reconnect();
    delay(2000);
    return;
  }

  // 1. Capture camera frame
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[ERROR] Frame capture failed");
    delay(500);
    return;
  }

  // 2. Connect to Render Cloud
  if (secureClient.connect(RENDER_HOST, RENDER_PORT)) {
    // 3. Send HTTP POST with raw JPEG binary
    secureClient.println("POST /api/detect HTTP/1.1");
    secureClient.println("Host: " + String(RENDER_HOST));
    secureClient.println("Content-Type: image/jpeg");
    secureClient.println("Content-Length: " + String(fb->len));
    secureClient.println("Connection: close");
    secureClient.println();

    // Send binary bytes
    secureClient.write(fb->buf, fb->len);

    // 4. Read response
    String response = "";
    long timeout = millis() + 5000;
    while (secureClient.connected() && millis() < timeout) {
      while (secureClient.available()) {
        char c = secureClient.read();
        response += c;
      }
    }
    secureClient.stop();

    // 5. Parse JSON Alert from response
    // Example response: {"status":"success", "alert":"hazard?type=fire", ...}
    int alertIdx = response.indexOf("\"alert\":");
    if (alertIdx != -1) {
      int startQuote = response.indexOf("\"", alertIdx + 8);
      int endQuote = response.indexOf("\"", startQuote + 1);
      if (startQuote != -1 && endQuote != -1) {
        String alert = response.substring(startQuote + 1, endQuote);
        if (alert != "null" && alert.length() > 0) {
          sendAlertToMaster(alert);
        }
      }
    }
  } else {
    Serial.println("[ERROR] Failed to connect to Render Host!");
    delay(1000);
  }

  // Return the frame buffer to free memory
  esp_camera_fb_return(fb);

  // Interval between frames (500ms - 800ms)
  delay(500);
}
