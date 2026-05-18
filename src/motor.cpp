#include "motor.h"
#include "encoder.h"
#include "servo_brake.h"
#include "imu_bridge.h"
#include <Arduino.h>

#define MOTOR_PIN_A D7
#define MOTOR_PIN_B D8
#define PWM_SPEED 800

#define REWIND_HOME_TICKS 25L
#define REWIND_MAX_MS 15000UL
#define REWIND_PROGRESS_LOG_MS 500UL
#define REWIND_WRONG_WAY_MARGIN_TICKS 200L

static bool windingActive = false;
static bool windingUsingReverse = true;
static bool windingSwitchedDirection = false;
static long windingStartTicks = 0;
static unsigned long windingStartMs = 0;
static unsigned long windingLastLogMs = 0;

void motorInit() {
    pinMode(MOTOR_PIN_A, OUTPUT);
    pinMode(MOTOR_PIN_B, OUTPUT);
    motorStop();
    Serial.println("[Motor] Initialized");
}

void motorForward() {
    digitalWrite(MOTOR_PIN_A, HIGH);
    digitalWrite(MOTOR_PIN_B, LOW);
    Serial.println("[Motor] Forward output: D7=HIGH D8=LOW");
}

void motorReverse() {
    digitalWrite(MOTOR_PIN_A, LOW);
    digitalWrite(MOTOR_PIN_B, HIGH);
    Serial.println("[Motor] Reverse output: D7=LOW D8=HIGH");
}

void motorStop() {
    digitalWrite(MOTOR_PIN_A, LOW);
    digitalWrite(MOTOR_PIN_B, LOW);
    windingActive = false;
}

bool motorIsWindingBack() {
    return windingActive;
}

void motorStartWindBack() {
    windingStartTicks = readTicks();
    Serial.printf("[Motor] Winding requested from ticks=%ld distance=%.3f m\n",
                  windingStartTicks,
                  readDistance());

    if (windingStartTicks <= REWIND_HOME_TICKS) {
        motorStop();
        servoBrakeRelease();
        Serial.println("[Motor] Winding skipped: already near home");
        return;
    }

    windingActive = true;
    windingUsingReverse = true;
    windingSwitchedDirection = false;
    windingStartMs = millis();
    windingLastLogMs = 0;
    servoBrakeRelease();
    motorReverse();
    Serial.println("[Motor] Winding started dir=reverse");
}

void motorUpdateWindBack() {
    if (!windingActive) return;

    const unsigned long now = millis();
    const long ticks = readTicks();

    if (ticks <= REWIND_HOME_TICKS) {
        motorStop();
        servoBrakeRelease();
        Serial.printf("[Motor] Winding complete at ticks=%ld distance=%.3f m\n",
                      readTicks(),
                      readDistance());
        return;
    }

    if (now - windingStartMs > REWIND_MAX_MS) {
        motorStop();
        servoBrakeRelease();
        Serial.printf("[Motor] Winding timeout at ticks=%ld distance=%.3f m\n",
                      ticks,
                      readDistance());
        return;
    }

    if (!windingSwitchedDirection && ticks > windingStartTicks + REWIND_WRONG_WAY_MARGIN_TICKS) {
        windingSwitchedDirection = true;
        windingUsingReverse = false;
        motorForward();
        Serial.printf("[Motor] Rewind direction switched at ticks=%ld\n", ticks);
    }

    if (now - windingLastLogMs >= REWIND_PROGRESS_LOG_MS) {
        windingLastLogMs = now;
        Serial.printf("[Motor] Winding ticks=%ld distance=%.3f m dir=%s\n",
                      ticks,
                      readDistance(),
                      windingUsingReverse ? "reverse" : "forward");
    }

    imuBridgeLoop();
}

void motorAbortWindBack() {
    if (windingActive) {
        Serial.printf("[Motor] Winding aborted at ticks=%ld distance=%.3f m\n",
                      readTicks(),
                      readDistance());
    }
    motorStop();
}

void motorWindBack() {
    motorStartWindBack();
}
