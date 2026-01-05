#include "encoder.h"
#include <Arduino.h>

// 编码器引脚（根据实际修改）
#define ENCODER_PIN_A D5
#define ENCODER_PIN_B D6

long encoderTicks = 0;        // 总步数
// 29589 ticks for 1.5 m => 1 tick ≈ 0.0000507 m
float distancePerTick = 0.0000507;
const int ENCODER_SIGN = -1; // Set to 1 or -1 to make pull-out distance positive

void IRAM_ATTR handleEncoderA() {
    // 简单双相编码器方向判定
    if (digitalRead(ENCODER_PIN_A) == HIGH) {
        if (digitalRead(ENCODER_PIN_B) == LOW)
            encoderTicks++;
        else
            encoderTicks--;
    } else {
        if (digitalRead(ENCODER_PIN_B) == HIGH)
            encoderTicks++;
        else
            encoderTicks--;
    }
}

void encoderInit() {
    pinMode(ENCODER_PIN_A, INPUT_PULLUP);
    pinMode(ENCODER_PIN_B, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(ENCODER_PIN_A), handleEncoderA, CHANGE);
    Serial.println("[Encoder] Initialized");
}

float readDistance() {
    return static_cast<float>(encoderTicks) * distancePerTick * ENCODER_SIGN;
}

long readTicks() {
    return encoderTicks * ENCODER_SIGN;
}
