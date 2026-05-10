#include "motor.h"
#include "encoder.h"
#include "servo_brake.h"
#include <Arduino.h>

#define MOTOR_PIN_A D7
#define MOTOR_PIN_B D8
#define PWM_SPEED   800 // PWM duty range: 0-1023

const float REWIND_HOME_DISTANCE_M = 0.005f; // Stop within 0.5 cm of the training start point.
const unsigned long REWIND_TIMEOUT_MS = 12000;

void motorInit() {
    pinMode(MOTOR_PIN_A, OUTPUT);
    pinMode(MOTOR_PIN_B, OUTPUT);
    motorStop();
    Serial.println("[Motor] Initialized");
}

void motorForward() {
    analogWrite(MOTOR_PIN_A, PWM_SPEED);
    analogWrite(MOTOR_PIN_B, 0);
}

void motorReverse() {
    analogWrite(MOTOR_PIN_A, 0);
    analogWrite(MOTOR_PIN_B, PWM_SPEED);
}

void motorStop() {
    analogWrite(MOTOR_PIN_A, 0);
    analogWrite(MOTOR_PIN_B, 0);
}

bool motorWindBack() {
    Serial.println("[Motor] Winding back to start position...");
    servoBrakeRelease();

    unsigned long startedAt = millis();
    while (readDistance() > REWIND_HOME_DISTANCE_M) {
        if (millis() - startedAt > REWIND_TIMEOUT_MS) {
            motorStop();
            Serial.println("ERROR: REWIND_TIMEOUT");
            return false;
        }
        motorReverse();
        delay(20);
    }

    motorStop();
    resetEncoder();
    servoBrakeRelease();
    Serial.println("REWIND_DONE");
    Serial.println("[Motor] Winding complete");
    return true;
}
