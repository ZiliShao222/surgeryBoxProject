#include <Arduino.h>
#include "wifi_udp_server.h"
#include "encoder.h"
#include "servo_brake.h"
#include "motor.h"
#include "events.h"
#include "config.h"
#include "signal_tester.h"

void setup() {
    Serial.begin(115200);
    Serial.println("[BOOT] SurgeryBox starting...");
    initWiFiHotspotUDP("surgeryBox", "12345678", 4210); // UDP mode
    initHttpEchoServer(); // HTTP /echo endpoint

    //initWiFiHotspot();      // Legacy TCP hotspot
    encoderInit();          // Encoder
    servoBrakeInit();       // Brake servo
    motorInit();            // Motor
    eventsInit();           // Random distance arrays
    signalTesterInit();     // Serial-to-UDP passthrough
}

void loop() {
    //handleWiFiCommands();   // Legacy TCP handler
    handleUDPMessages();
    handleHttpServer();
    processEncoderEvents(); // Check encoder distance and trigger events

    // Periodically log encoder ticks, distance, and speed (only when position changes)
    static unsigned long lastPrint = 0;
    static float lastDist = 0.0f;
    static long lastTicks = 0;
    unsigned long now = millis();
    if (now - lastPrint >= 200) {
        float dist = readDistance();
        float dt = (now - lastPrint) / 1000.0f;
        float speed = dt > 0 ? (dist - lastDist) / dt : 0.0f; // m/s
        long ticks = readTicks();
        lastPrint = now;
        if (ticks != lastTicks) {
            lastTicks = ticks;
            lastDist = dist;
            Serial.printf("[Encoder] ticks=%ld distance=%.3f m speed=%.3f m/s\n",
                          ticks, dist, speed);

            // Send real-time position/speed only after Start triggers a sequence
            if (sequenceRunning) {
                float posCm = dist * 100.0f;
                float speedCmps = speed * 100.0f;
                sendUDPMessageToLast("POS:" + String(posCm, 2));
                sendUDPMessageToLast("SPEED:" + String(speedCmps, 2));
            }
        }
    }

    signalTesterLoop();
}
