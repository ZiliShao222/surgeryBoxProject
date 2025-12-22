#include <Arduino.h>
#include "wifi_server.h"
#include "encoder.h"
#include "servo_brake.h"
#include "motor.h"
#include "events.h"
#include "configs.h"

void setup() {
    Serial.begin(115200);
    Serial.println("[BOOT] MyBrakeMachine starting...");

    initWiFiHotspot();      // 启动WiFi热点
    encoderInit();          // 初始化编码器
    servoBrakeInit();       // 初始化舵机
    motorInit();            // 初始化电机
    eventsInit();           // 加载10组随机距离数组
}

void loop() {
    handleWiFiCommands();   // 检查上位机发来的指令
    processEncoderEvents(); // 检查编码器距离并触发事件
}
