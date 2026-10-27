/*
 =========================================================================================
   SMART CAP - ESP32-CAM AI CLIENT (ZERO LOCAL IP CONFIGURATION)
   GP Siwan / Bihar Talent Hunt
 =========================================================================================
   Description:
   Yeh sketch ESP32-CAM par flash hoga. Yeh camera se photo lega aur direct Render Server
   par bhejega (HTTPS POST). 

   Faayda:
   1. Kisi bhi local IP address (10.x.x.x ya 192.168.x.x) ki zaroorat nahi hai!
   2. Hotspot badal jaye ya IP badal jaye, isko koi farak nahi padega.
   3. Sirf Render Cloud Domain (smartcap-ai.onrender.com) se connect hota hai.
 =========================================================================================
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>

// ==================== 1. WI-FI CREDENTIALS ====================
// Apne Mobile Hotspot ka Naam aur Password daalein:
const char* ssid     = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_HOTSPOT_PASSWORD";

// ==================== 2. RENDER CLOUD SERVER ====================
// Aapka Render domain (bina "https://" aur bina "/" ke):
const char* RENDER_HOST = "smartcap-ai.onrender.com"; 
const int   RENDER_PORT = 443; // HTTPS Port
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

  // Frame size: QVGA (320x240) - fast upload over mobile data
  if (psramFound()) {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
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
  Serial.println("\n==============================================");
  Serial.println("  SMART CAP - ESP32-CAM CLOUD UPLOADER        ");
  Serial.println("  (100% Zero Local IP - Direct to Render)     ");
  Serial.println("==============================================");

  setupCamera();

  // Connect to Wi-Fi
  Serial.printf("Connecting to Wi-Fi: %s", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected!");
  Serial.print("ESP32-CAM IP: ");
  Serial.println(WiFi.localIP());

  secureClient.setInsecure(); // No certificate check needed
  secureClient.setTimeout(5);
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

    // Stream binary image bytes
    secureClient.write(fb->buf, fb->len);

    Serial.printf("📸 [FRAME SENT] %d bytes uploaded to Render!\n", fb->len);

    // Read response briefly
    long timeout = millis() + 4000;
    while (secureClient.connected() && millis() < timeout) {
      while (secureClient.available()) {
        char c = secureClient.read();
        // Discard response characters, server processes it in cloud
      }
    }
    secureClient.stop();
  } else {
    Serial.println("[ERROR] Failed to connect to Render Host!");
    delay(1000);
  }

  // Free frame buffer
  esp_camera_fb_return(fb);

  // Interval between captures (400ms - 600ms)
  delay(400);
}
