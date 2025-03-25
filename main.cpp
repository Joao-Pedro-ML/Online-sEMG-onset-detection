// #include <Arduino.h>

// hw_timer_t *My_timer = NULL;

// const int emgPin = 34;
// volatile bool coleta = false;
// uint16_t emgValue = 0;

// void IRAM_ATTR onTimer() {
//     coleta = true;
// }

// void coleta_e_envio(void *pvParameters) {
//     while (true) {
//         if (coleta) {
//             timerWrite(My_timer, 0);
//             emgValue = analogRead(emgPin);

//             Serial.write(0xCC);  // Byte inicial para sincronização
//             Serial.write(emgValue >> 8);   // Envia byte mais significativo (MSB)
//             Serial.write(emgValue & 0xFF); // Envia byte menos significativo (LSB)

//             coleta = false;
//         }
//         vTaskDelay(pdMS_TO_TICKS(1));
//     }
// }

// void setup() {
//     Serial.begin(115200);
//     pinMode(emgPin, INPUT);

//     My_timer = timerBegin(0, 80, true); // Timer 0, divisor 80 (1 tick = 1 µs)
//     timerAttachInterrupt(My_timer, &onTimer, true);
//     timerAlarmWrite(My_timer, 1000, true); // 1000 µs = 1 ms -> 1000 Hz
//     timerAlarmEnable(My_timer);

//     xTaskCreate(coleta_e_envio, "ColetaEnvioTask", 10000, NULL, 1, NULL);
// }

// void loop() {
// }


////////////////////////////////////////////////////////////////////////////////////
// #include <Arduino.h>
// #include "BluetoothSerial.h"

// BluetoothSerial SerialBT;

// hw_timer_t *My_timer = NULL;

// const int emgPin = 34;
// volatile bool coleta = false;
// uint16_t emgValue = 0;

// void IRAM_ATTR onTimer() {
//     coleta = true;
// }

// void coleta_e_envio(void *pvParameters) {
//     while (true) {
//         if (coleta) {
//             timerWrite(My_timer, 0);
//             emgValue = analogRead(emgPin);

//             SerialBT.write(0xCC);           // Byte de sincronização
//             SerialBT.write(emgValue >> 8);  // Byte mais significativo (MSB)
//             SerialBT.write(emgValue & 0xFF); // Byte menos significativo (LSB)

//             coleta = false;
//         }
//         vTaskDelay(pdMS_TO_TICKS(1));
//     }
// }

// void setup() {
//     Serial.begin(115200);  // Apenas para debug via Serial USB
//     SerialBT.begin("EMG_Sensor"); // Nome do dispositivo Bluetooth
//     pinMode(emgPin, INPUT);

//     My_timer = timerBegin(0, 80, true); // Timer 0, divisor 80 (1 tick = 1 µs)
//     timerAttachInterrupt(My_timer, &onTimer, true);
//     timerAlarmWrite(My_timer, 1000, true); // 1000 µs = 1 ms -> 1000 Hz
//     timerAlarmEnable(My_timer);

//     xTaskCreate(coleta_e_envio, "ColetaEnvioTask", 10000, NULL, 1, NULL);
// }

// void loop() {
// }


////////////////////////////////// %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% /////////////////////////////////

#include <Arduino.h>

#define RXD2 16
#define TXD2 17


hw_timer_t *My_timer = NULL;

const int emgPin = 34;
volatile bool coleta = false;
uint16_t emgValue = 0;

void IRAM_ATTR onTimer() {
    coleta = true;
}

void coleta_e_envio(void *pvParameters) {
    while (true) {
        if (coleta) {
            timerWrite(My_timer, 0);
            emgValue = analogRead(emgPin);

            Serial.write(0xCC);           // Byte de sincronização
            Serial.write(emgValue >> 8);  // Byte mais significativo (MSB)
            Serial.write(emgValue & 0xFF); // Byte menos significativo (LSB)

            coleta = false;
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

void setup() {
    Serial.begin(115200);
    Serial2.begin(115200, SERIAL_8N1, RXD2, TXD2);
    pinMode(emgPin, INPUT);

    My_timer = timerBegin(0, 80, true); // Timer 0, divisor 80 (1 tick = 1 µs)
    timerAttachInterrupt(My_timer, &onTimer, true);
    timerAlarmWrite(My_timer, 1000, true); // 1000 µs = 1 ms -> 1000 Hz
    timerAlarmEnable(My_timer);

    xTaskCreate(coleta_e_envio, "ColetaEnvioTask", 10000, NULL, 1, NULL);
}

void loop() {
}
