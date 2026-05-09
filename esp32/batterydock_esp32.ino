/*
 * ═══════════════════════════════════════════════════════════════
 * BatteryDock — ESP32 Telemetry Reference Sender
 * ═══════════════════════════════════════════════════════════════
 * 
 * This file is your "Sending Logic". 
 * You should copy the WiFi and HTTP parts of this code into 
 * your existing sensor firmware.
 *
 * ═══════════════════════════════════════════════════════════════
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// [SECTION 1: NETWORK CONFIGURATION]
// Change these three lines to match your setup:
const char* WIFI_SSID     = "YOUR_WIFI_NAME";      // Line 18: Your WiFi Name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";  // Line 19: Your WiFi Password
const char* LAPTOP_IP     = "192.168.1.100";      // Line 20: Your Laptop's IPv4

// The backend "door" (endpoint) where data is received
String serverURL = "http://" + String(LAPTOP_IP) + ":8000/telemetry";

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi Connected!");
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    
    // [SECTION 2: YOUR SENSOR DATA]
    // Replace these variables with your existing sensor readings:
    float myVoltage    = 3.92;  // Replace with your voltage variable
    float myCurrent    = 2.15;  // Replace with your current variable
    float myTemp       = 31.5;  // Replace with your temperature variable
    float mySoc        = 85.0;  // Replace with your battery percentage variable
    float myHumidity   = 42.0;  // Replace with your humidity variable
    int   myCycle      = 124;   // Replace with your cycle count variable
    float myCapacity   = 0.92;  // Replace with your capacity variable

    // [SECTION 3: JSON PACKAGING]
    // This creates the "envelope" to send to the backend
    JsonDocument doc;
    doc["voltage"]            = myVoltage;
    doc["current"]            = myCurrent;
    doc["temperature"]        = myTemp;
    doc["battery_percentage"] = mySoc;
    doc["humidity"]           = myHumidity;
    doc["cycle"]              = myCycle;
    doc["capacity"]           = myCapacity;

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    // [SECTION 4: SENDING TO BACKEND]
    HTTPClient http;
    http.begin(serverURL);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST(jsonPayload);
    
    if (httpResponseCode > 0) {
      Serial.print("✅ Data Sent! Response: ");
      Serial.println(http.getString());
    } else {
      Serial.print("❌ Send Error: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  }
  
  delay(2000); // Send every 2 seconds
}
