#include "encoder.h"
#include <Arduino.h>

#define ENCODER_PIN_A D5
#define ENCODER_PIN_B D6

volatile long encoderTicks = 0;
volatile unsigned long encoderEdgesA = 0;
volatile unsigned long encoderEdgesB = 0;
volatile uint8_t lastAB = 0;

float distancePerTick = 0.0000507; // 29589 ticks for 1.5 m.
const int ENCODER_SIGN = -1;       // Keep this legacy test firmware behavior unchanged.

static uint8_t readABState() {
    return (digitalRead(ENCODER_PIN_A) ? 0x02 : 0x00) |
           (digitalRead(ENCODER_PIN_B) ? 0x01 : 0x00);
}

static int8_t decodeQuadrature(uint8_t previous, uint8_t current) {
    switch ((previous << 2) | current) {
        case 0b0001:
        case 0b0111:
        case 0b1110:
        case 0b1000:
            return 1;
        case 0b0010:
        case 0b0100:
        case 0b1101:
        case 0b1011:
            return -1;
        default:
            return 0;
    }
}

static void IRAM_ATTR updateEncoderFromPins(bool edgeOnA) {
    if (edgeOnA) {
        encoderEdgesA++;
    } else {
        encoderEdgesB++;
    }

    uint8_t currentAB = readABState();
    encoderTicks += decodeQuadrature(lastAB, currentAB);
    lastAB = currentAB;
}

void IRAM_ATTR handleEncoderA() {
    updateEncoderFromPins(true);
}

void IRAM_ATTR handleEncoderB() {
    updateEncoderFromPins(false);
}

void encoderInit() {
    pinMode(ENCODER_PIN_A, INPUT_PULLUP);
    pinMode(ENCODER_PIN_B, INPUT_PULLUP);
    lastAB = readABState();
    attachInterrupt(digitalPinToInterrupt(ENCODER_PIN_A), handleEncoderA, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_PIN_B), handleEncoderB, CHANGE);
    Serial.println("[Encoder] Initialized with A/B dual-edge diagnostics");
}

float readDistance() {
    return static_cast<float>(readTicks()) * distancePerTick;
}

long readTicks() {
    return readRawTicks() * ENCODER_SIGN;
}

long readRawTicks() {
    noInterrupts();
    long ticks = encoderTicks;
    interrupts();
    return ticks;
}

int readEncoderPinA() {
    return digitalRead(ENCODER_PIN_A);
}

int readEncoderPinB() {
    return digitalRead(ENCODER_PIN_B);
}

unsigned long readEncoderEdgesA() {
    noInterrupts();
    unsigned long count = encoderEdgesA;
    interrupts();
    return count;
}

unsigned long readEncoderEdgesB() {
    noInterrupts();
    unsigned long count = encoderEdgesB;
    interrupts();
    return count;
}

void resetEncoderDiagnostics() {
    uint8_t currentAB = readABState();
    noInterrupts();
    encoderTicks = 0;
    encoderEdgesA = 0;
    encoderEdgesB = 0;
    lastAB = currentAB;
    interrupts();
}
