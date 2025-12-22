#include "servo_brake.h"
#include <Servo.h>
#include <pins_arduino.h>
#include <HardwareSerial.h>

Servo brakeServo;

// 假设这几个角度值对应不同刹车状态
#define BRAKE_LOCK_ANGLE  150  // 锁死
#define BRAKE_WEAK_ANGLE  120  // 弱阻尼
#define BRAKE_RELEASE_ANGLE 90 // 释放

void servoBrakeInit() {
    brakeServo.attach(D2); // GPIO4
    brakeServo.write(BRAKE_RELEASE_ANGLE);
    Serial.println("[Servo] Brake initialized");
}

void servoBrakeLock() {
    brakeServo.write(BRAKE_LOCK_ANGLE);
    Serial.println("[Servo] Brake locked");
}

void servoBrakeWeak() {
    brakeServo.write(BRAKE_WEAK_ANGLE);
    Serial.println("[Servo] Weak damping");
}

void servoBrakeRelease() {
    brakeServo.write(BRAKE_RELEASE_ANGLE);
    Serial.println("[Servo] Brake released");
}
