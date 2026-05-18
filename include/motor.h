#ifndef MOTOR_H
#define MOTOR_H

void motorInit();
void motorForward();
void motorReverse();
void motorStartWindBack();
void motorUpdateWindBack();
void motorWindBack();
void motorStop();
void motorAbortWindBack();
bool motorIsWindingBack();

#endif

