/*
 =========================================================================================
   SMART CAP - MAIN ESP32 CLOUD AUDIO ENGINE (ZERO LOCAL IP CONFIGURATION)
   GP Siwan / Bihar Talent Hunt
 =========================================================================================
   Description:
   Yeh sketch Main ESP32 (Speaker / DFPlayer Mini) par flash hoga.
   Yeh board direct Render Cloud Server (smartcap-ai.onrender.com) se alert poll karega.
   
   FAAYDA:
   1. Kisi bhi local IP address (10.x.x.x ya 192.168.x.x) ki zaroorat nahi hai!
   2. Hotspot badalne par ya IP change hone par koi dikkat nahi aayegi.
   3. Jaise hi Render AI kuch detect karega (Kutta, Gadi, Aag, Shridev Bhaiya),
      yeh board turant DFPlayer se Hindi voice aawaz bolega!
 =========================================================================================
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HardwareSerial.h>
#include "DFRobotDFPlayerMini.h"

// ==================== 1. WI-FI CREDENTIALS ====================
// Apne Mobile Hotspot ka Naam aur Password yahan daalein:
const char* ssid     = "YOUR_HOTSPOT_NAME";
const char* password = "YOUR_HOTSPOT_PASSWORD";

// ==================== 2. RENDER CLOUD SERVER ====================
// Aapka Render domain (bina "https://" aur bina "/" ke):
const char* RENDER_HOST = "smartcap-ai.onrender.com";
const int   RENDER_PORT = 443; // HTTPS Port

// ==================== 3. DFPLAYER MINI PINS ====================
// ESP32 HardwareSerial2:
// ESP32 Pin 16 (RX2) -> DFPlayer TX Pin
// ESP32 Pin 17 (TX2) -> DFPlayer RX Pin (1K resistor ke sath)
#define DFPLAYER_RX_PIN 16
#define DFPLAYER_TX_PIN 17

HardwareSerial dfpSerial(2);
DFRobotDFPlayerMini myDFPlayer;
WiFiClientSecure secureClient;

int lastAlertId = 0;
unsigned long lastPollTime = 0;
const unsigned long POLL_INTERVAL = 400; // Har 400ms me cloud se check karega

// ==================== 4. SOUND TRACK NUMBERS (SD Card Files) ====================
// DFPlayer SD card par files ka number:
// 0001.mp3 -> Shridev Bhaiya
// 0002.mp3 -> Koi vyakti samne hai
// 0003.mp3 -> Kutta (Dog) samne hai
// 0004.mp3 -> Janwar / Gaay (Cow) samne hai
// 0005.mp3 -> Gadi (Car) samne hai
// 0006.mp3 -> Bike / Motorcycle samne hai
// 0007.mp3 -> Aag (Fire) samne hai
// 0008.mp3 -> Kamba / Rukawat (Pole) samne hai
void playVoiceAlert(String endpoint, String message) {
  Serial.println("\n🔊 [VOICE ALERT RECEIVED FROM CLOUD]: " + message);
  Serial.println("👉 Command: " + endpoint);

  int trackNumber = 0;

  if (endpoint.indexOf("shridev") >= 0) {
    trackNumber = 1;
    Serial.println("👑 Shridev Bhaiya track playing (0001.mp3)...");
  } else if (endpoint.indexOf("person") >= 0) {
    trackNumber = 2;
    Serial.println("👤 Unknown Person track playing (0002.mp3)...");
  } else if (endpoint.indexOf("dog") >= 0) {
    trackNumber = 3;
    Serial.println("🐕 Dog track playing (0003.mp3)...");
  } else if (endpoint.indexOf("cow") >= 0) {
    trackNumber = 4;
    Serial.println("🐄 Cow track playing (0004.mp3)...");
  } else if (endpoint.indexOf("car") >= 0) {
    trackNumber = 5;
    Serial.println("🚗 Car track playing (0005.mp3)...");
  } else if (endpoint.indexOf("bike") >= 0) {
    trackNumber = 6;
    Serial.println("🏍️ Bike track playing (0006.mp3)...");
  } else if (endpoint.indexOf("fire") >= 0) {
    trackNumber = 7;
    Serial.println("🔥 Fire track playing (0007.mp3)...");
  } else if (endpoint.indexOf("pole") >= 0) {
    trackNumber = 8;
    Serial.println("🚧 Low obstacle / Pole track playing (0008.mp3)...");
  }

  if (trackNumber > 0) {
    myDFPlayer.play(trackNumber);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==============================================");
  Serial.println("  SMART CAP - MAIN ESP32 CLOUD AUDIO ENGINE   ");
  Serial.println("  (100% Zero Local IP - Cloud Polling)        ");
  Serial.println("==============================================");

  // Initialize DFPlayer Serial
  dfpSerial.begin(9600, SERIAL_8N1, DFPLAYER_RX_PIN, DFPLAYER_TX_PIN);
  delay(500);

  Serial.println("[DFPLAYER] Connecting to DFPlayer Mini...");
  if (!myDFPlayer.begin(dfpSerial)) {
    Serial.println("⚠️ DFPlayer check: Check SD Card & Wiring (Pins 16 & 17)");
  } else {
    Serial.println("✅ DFPlayer Mini Online!");
    myDFPlayer.volume(28); // Volume set (0 to 30)
    delay(200);
  }

  // Connect to Mobile Hotspot
  Serial.printf("Connecting to Wi-Fi: %s", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi Connected Successfully!");
  Serial.print("Board IP: ");
  Serial.println(WiFi.localIP());

  secureClient.setInsecure(); // No certificate check needed
  secureClient.setTimeout(4); // 4 seconds timeout

  Serial.println("🚀 Connected to Cloud! Listening for alerts...\n");
}

void pollCloudAlert() {
  if (WiFi.status() != WL_CONNECTED) return;

  if (secureClient.connect(RENDER_HOST, RENDER_PORT)) {
    // Request lightweight plain-text alert endpoint
    String url = "/api/poll-alert-simple?last_id=" + String(lastAlertId);
    secureClient.println("GET " + url + " HTTP/1.1");
    secureClient.println("Host: " + String(RENDER_HOST));
    secureClient.println("Connection: close");
    secureClient.println();

    // Read response line by line
    String responseBody = "";
    bool isBody = false;
    long timeout = millis() + 3000;

    while (secureClient.connected() && millis() < timeout) {
      while (secureClient.available()) {
        String line = secureClient.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) {
          isBody = true; // Empty line separates headers from body
          continue;
        }
        if (isBody) {
          responseBody = line;
          break;
        }
      }
      if (responseBody.length() > 0) break;
    }
    secureClient.stop();

    // Response Format: "NEW:<endpoint>:<alert_id>:<message>"
    // Example: "NEW:person?name=unknown:4:Koi Vyakti Samne Hai!"
    if (responseBody.startsWith("NEW:")) {
      int firstColon  = responseBody.indexOf(':');
      int secondColon = responseBody.indexOf(':', firstColon + 1);
      int thirdColon  = responseBody.indexOf(':', secondColon + 1);

      if (firstColon != -1 && secondColon != -1 && thirdColon != -1) {
        String endpoint = responseBody.substring(firstColon + 1, secondColon);
        int alertId     = responseBody.substring(secondColon + 1, thirdColon).toInt();
        String message  = responseBody.substring(thirdColon + 1);

        if (alertId > lastAlertId) {
          lastAlertId = alertId;
          playVoiceAlert(endpoint, message);
        }
      }
    }
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi reconnecting...");
    WiFi.reconnect();
    delay(2000);
    return;
  }

  // Poll cloud for new alerts
  if (millis() - lastPollTime >= POLL_INTERVAL) {
    lastPollTime = millis();
    pollCloudAlert();
  }
}
