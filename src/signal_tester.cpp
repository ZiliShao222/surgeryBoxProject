#include "signal_tester.h"
#include "wifi_udp_server.h"
#include <Arduino.h>

void signalTesterInit() {
    Serial.println("[SignalTester] Ready. USB serial commands are routed directly to the MCU.");
    Serial.println("[SignalTester] Example: HELLO_PC / Start / OK / OK1 / OK2 / Winding");
}

void signalTesterLoop() {
    // Serial commands are handled first in loop() so the training PC gets the
    // lowest possible latency on Start/OK/Winding.
}
