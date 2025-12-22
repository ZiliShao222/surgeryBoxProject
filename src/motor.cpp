#include "motor.h"
#include "encoder.h"
#include "servo_brake.h"
#include <Arduino.h>

#define MOTOR_PIN_A D7
#define MOTOR_PIN_B D8
#define PWM_SPEED   800 // PWM占空比范围 0-1023

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

void motorWindBack() {
    Serial.println("[Motor] Winding back...");
    while (readDistance() > 0.5) {
        motorReverse();
        delay(50);
    }
    motorStop();
    servoBrakeRelease();
    Serial.println("[Motor] Winding complete");
}
