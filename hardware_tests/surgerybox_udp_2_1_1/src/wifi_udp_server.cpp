#include "wifi_udp_server.h"
#include "servo_brake.h"
#include "motor.h"
#include "events.h"
#include "encoder.h"
#include "config.h"
#include <Arduino.h>

static String readDigitalPinsSnapshot() {
    const uint8_t pins[] = {D0, D1, D2, D3, D4, D5, D6, D7, D8};
    const char* names[] = {"D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"};
    String out = "PINS:";
    for (size_t i = 0; i < sizeof(pins) / sizeof(pins[0]); ++i) {
        if (i > 0) out += ",";
        out += names[i];
        out += "=";
        out += String(digitalRead(pins[i]));
    }
    return out;
}

static String readEncoderSnapshot() {
    return "ENC:raw=" + String(readRawTicks()) +
           ",ticks=" + String(readTicks()) +
           ",dist_m=" + String(readDistance(), 4) +
           ",A=" + String(readEncoderPinA()) +
           ",B=" + String(readEncoderPinB()) +
           ",edgeA=" + String(readEncoderEdgesA()) +
           ",edgeB=" + String(readEncoderEdgesB()) +
           ",seq=" + String(sequenceRunning ? 1 : 0);
}

WiFiUDP Udp;
uint16_t localPort;
IPAddress lastRemoteIp;
uint16_t lastRemotePort;
char packetBuffer[255];
ESP8266WebServer httpServer(80);

static bool readIncomingUDP(String &msg) {
    int packetSize = Udp.parsePacket();
    if (!packetSize) return false;
    lastRemoteIp = Udp.remoteIP();
    lastRemotePort = Udp.remotePort();
    int len = Udp.read(packetBuffer, sizeof(packetBuffer) - 1);
    if (len > 0) packetBuffer[len] = '\0';
    msg = String(packetBuffer);
    msg.trim();
    return true;
}

void initWiFiHotspotUDP(const char* ssid, const char* password, uint16_t listenPort) {
    WiFi.softAP(ssid, password);
    localPort = listenPort;
    Udp.begin(localPort);
    Serial.printf("[WiFi UDP] Hotspot started. SSID=%s, Port=%u\n", ssid, localPort);
    Serial.print("[WiFi UDP] Board IP: ");
    Serial.println(WiFi.softAPIP());
}

void initHttpEchoServer() {
    httpServer.on("/echo", HTTP_ANY, []() {
        String body = httpServer.arg("plain");
        Serial.printf("[HTTP] /echo received (%d bytes): %s\n", body.length(), body.c_str());
        httpServer.send(200, "text/plain", body);
    });
    httpServer.onNotFound([]() { httpServer.send(404, "text/plain", "Not Found"); });
    httpServer.begin();
    Serial.println("[HTTP] Echo server started on port 80");
}

void handleHttpServer() {
    httpServer.handleClient();
}

void handleUDPMessages() {
    String msg;
    if (!readIncomingUDP(msg)) return;

    Serial.printf("[WiFi UDP] Received from %s:%u : %s\n",
                  lastRemoteIp.toString().c_str(),
                  lastRemotePort,
                  msg.c_str());

    // Echo back for monitoring
    sendUDPMessageToLast(msg);

    if (msg == "Start") {
        startEventSequence();
        sendUDPMessageToLast("ACK: Start");
    } else if (msg == "Stop") {
        servoBrakeLock();
        sendUDPMessageToLast("ACK: Stop");
    } else if (msg == "Winding") {
        motorWindBack();
        sendUDPMessageToLast("ACK: Winding");
    } else if (msg == "ENC" || msg == "ENC?") {
        sendUDPMessageToLast(readEncoderSnapshot());
    } else if (msg == "ZERO" || msg == "RSTENC" || msg == "RESET_ENC") {
        resetEncoderDiagnostics();
        sendUDPMessageToLast("ACK: ZERO");
        sendUDPMessageToLast(readEncoderSnapshot());
    } else if (msg == "PINS" || msg == "PINS?") {
        sendUDPMessageToLast(readDigitalPinsSnapshot());
    } else {
        sendUDPMessageToLast("ACK: " + msg);
    }
}

void sendUDPMessage(const IPAddress& ip, uint16_t port, const String& msg) {
    Serial.printf("[WiFi UDP] Send to %s:%u : %s\n", ip.toString().c_str(), port, msg.c_str());
    Udp.beginPacket(ip, port);
    Udp.write(msg.c_str());
    Udp.endPacket();
}

void sendUDPMessageToLast(const String& msg) {
    if (lastRemoteIp) {
        sendUDPMessage(lastRemoteIp, lastRemotePort, msg);
    }
}

void sendSignal(const String& sig) {
    sendUDPMessageToLast(sig);
    Serial.printf("[WiFi UDP] Signal sent: %s\n", sig.c_str());
}

void waitForCmd(const String& target) {
    while (true) {
        String msg;
        if (readIncomingUDP(msg)) {
            Serial.printf("[WiFi UDP] WaitForCmd got: %s\n", msg.c_str());
            if (msg == target) return;
        }
        delay(10);
    }
}

String waitForCmdAny(std::initializer_list<String> targets) {
    while (true) {
        String msg;
        if (readIncomingUDP(msg)) {
            Serial.printf("[WiFi UDP] WaitForCmdAny got: %s\n", msg.c_str());
            for (auto &t : targets) {
                if (msg == t) return msg;
            }
        }
        delay(10);
    }
}

void waitShortPull() {
    float startDist = readDistance();
    while (readDistance() < startDist + 0.5) {
        delay(10);
    }
}
