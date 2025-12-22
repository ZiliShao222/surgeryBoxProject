#include "encoder.h"
#include <Arduino.h>

// 编码器引脚（根据实际更改）
#define ENCODER_PIN_A D5
#define ENCODER_PIN_B D6

long encoderTicks = 0; // 总步数
float distancePerTick = 0.01; // 每步转换成距离（单位：米，可根据线径调整）

void IRAM_ATTR handleEncoderA() {
    // 简单双相编码器方向判断
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
    return encoderTicks * distancePerTick;
}
