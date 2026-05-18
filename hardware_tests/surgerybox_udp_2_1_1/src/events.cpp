#include <Arduino.h>
#include "events.h"
#include "config.h"
#include "encoder.h"
#include "servo_brake.h"
#include "wifi_udp_server.h"

float distanceArrays[10][4];
float currentArray[4];
bool sequenceRunning = false;
bool eventTriggered[4] = {false, false, false, false};

void eventsInit() {
    // 预设10组距离（单位：m），范围：Pain(0.05-0.15) Pain2(0.15-0.25) HighDamp(0.25-0.35) LowDamp(0.35-0.45)
    const float preset[10][4] = {
        {0.06f, 0.18f, 0.27f, 0.38f},
        {0.08f, 0.20f, 0.30f, 0.42f},
        {0.05f, 0.17f, 0.28f, 0.36f},
        {0.07f, 0.19f, 0.33f, 0.44f},
        {0.09f, 0.22f, 0.31f, 0.40f},
        {0.10f, 0.21f, 0.29f, 0.37f},
        {0.12f, 0.24f, 0.32f, 0.43f},
        {0.11f, 0.23f, 0.34f, 0.39f},
        {0.13f, 0.25f, 0.35f, 0.45f},
        {0.14f, 0.18f, 0.26f, 0.41f}
    };
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j < 4; j++) distanceArrays[i][j] = preset[i][j];
        Serial.printf("[EVENT] Array #%d -> Pain=%.2f, Pain2=%.2f, HighDamp=%.2f, LowDamp=%.2f\n",
                      i, distanceArrays[i][0], distanceArrays[i][1], distanceArrays[i][2], distanceArrays[i][3]);
    }
}

void startEventSequence() {
    int idx = random(0, 10);
    for (int i = 0; i < 4; i++) {
        currentArray[i] = distanceArrays[idx][i];
        eventTriggered[i] = false;
    }
    sequenceRunning = true;
    Serial.printf("[EVENT] Sequence started: Array #%d -> Pain=%.2f, Pain2=%.2f, HighDamp=%.2f, LowDamp=%.2f\n",
                  idx, currentArray[0], currentArray[1], currentArray[2], currentArray[3]);
    // 将选中的序列发送给上位机
    String seqMsg = "SEQ:" + String(idx) + "," +
                    String(currentArray[0] * 100.0f, 2) + "," +
                    String(currentArray[1] * 100.0f, 2) + "," +
                    String(currentArray[2] * 100.0f, 2) + "," +
                    String(currentArray[3] * 100.0f, 2);
    sendUDPMessageToLast(seqMsg);
}

void runTestFlow() {
    // 测试流已禁用
    Serial.println("[TEST] runTestFlow disabled");
}

void processEncoderEvents() {
    if (!sequenceRunning) return;
    float dist = readDistance();

    // Pain
    if (!eventTriggered[0] && dist >= currentArray[0]) {
        sendSignal("Pain");
        eventTriggered[0] = true;
        Serial.printf("[EVENT] Pain at %.3f m\n", dist);
    }
    // Pain2
    if (!eventTriggered[1] && dist >= currentArray[1]) {
        sendSignal("Pain2");
        eventTriggered[1] = true;
        Serial.printf("[EVENT] Pain2 at %.3f m\n", dist);
    }
    // HighDamp
    if (!eventTriggered[2] && dist >= currentArray[2]) {
        eventTriggered[2] = true;
        sendSignal("HighDamp");
        Serial.printf("[EVENT] HighDamp at %.3f m -> Lock brake, wait OK\n", dist);
        servoBrakeLock();
        waitForCmd("OK");
        servoBrakeRelease();
        Serial.println("[EVENT] HighDamp cleared, brake released");
    }
    // LowDamp + weak brake
    if (!eventTriggered[3] && dist >= currentArray[3]) {
        eventTriggered[3] = true;
        sendSignal("LowDamp");
        Serial.printf("[EVENT] LowDamp at %.3f m -> Weak brake, wait OK1/Continue\n", dist);
        servoBrakeWeak();
        String cmd = waitForCmdAny({"OK1", "Continue"});
        if (cmd == "OK1") {
            Serial.println("[EVENT] OK1 received -> release brake");
            servoBrakeRelease();
        } else if (cmd == "Continue") {
            Serial.println("[EVENT] Continue received -> wait short pull, send Keep");
            waitShortPull();
            sendSignal("Keep");
            waitForCmd("OK2");
            servoBrakeRelease();
            Serial.println("[EVENT] OK2 received -> release brake");
        }
        sequenceRunning = false;
        Serial.println("[EVENT] Sequence completed");
    }
}
