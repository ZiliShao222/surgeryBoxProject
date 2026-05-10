#include "signal_tester.h"
#include "wifi_udp_server.h"
#include <Arduino.h>

String serialInputBuffer = "";

void signalTesterInit() {
    Serial.println("[SignalTester] Ready. Type a command in Serial Monitor.");
    Serial.println("[SignalTester] Example: Start / Stop / Winding / OK / OK1 / Continue / OK2");
}

void signalTesterLoop() {
    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\n' || c == '\r') {
            if (serialInputBuffer.length() > 0) {
                handleHardwareCommand(serialInputBuffer, false);
                Serial.printf("[SignalTester] Command handled: %s\n", serialInputBuffer.c_str());
                serialInputBuffer = "";
            }
        } else {
            serialInputBuffer += c;
        }
    }
}
