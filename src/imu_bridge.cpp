#include "imu_bridge.h"

#include <Arduino.h>
#include <SoftwareSerial.h>

// IMU wiring for the ESP8266 D1 board:
//   IMU 3V3 -> ESP8266 3.3V
//   IMU GND -> ESP8266 GND
//   IMU TX  -> ESP8266 D1
// IMU RX is not required for the current transparent-forwarding mode.
//
// D5/D6 are used by the encoder, D7/D8 by the motor, and D2 by the brake servo.
// Keep the IMU on D1 so it does not fight the existing hardware.
#define IMU_RX_PIN D1
#define IMU_UNUSED_TX_PIN D0
#define IMU_BAUD 115200

static SoftwareSerial imuSerial(IMU_RX_PIN, IMU_UNUSED_TX_PIN);

void imuBridgeInit() {
    imuSerial.begin(IMU_BAUD);
    Serial.println("[IMU] Transparent bridge ready: IMU TX -> D1, USB serial -> COM3");
}

void imuBridgeLoop() {
    uint8_t buffer[64];
    size_t count = 0;

    while (imuSerial.available() && count < sizeof(buffer)) {
        buffer[count++] = static_cast<uint8_t>(imuSerial.read());
    }

    if (count > 0) {
        Serial.write(buffer, count);
    }
}
