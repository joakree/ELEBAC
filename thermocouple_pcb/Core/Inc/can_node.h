/*
 * can_node.h
 *
 *  Created on: 27. apr. 2026
 *      Author: joaki
 */

#ifndef CAN_NODE_H
#define CAN_NODE_H

#include "stm32g0xx_hal.h"

/* CAN IDs for sensor nodes */
#define CAN_ID_THERMOCOUPLE_1    0x001
#define CAN_ID_THERMOCOUPLE_2    0x002
#define CAN_ID_STRAIN_NODE_1     0x003
#define CAN_ID_STRAIN_NODE_2     0x004

/* Temperature scaling factor — °C × 10 for 0.1°C resolution */
#define CAN_TEMP_SCALE           10

/*
 * CAN message format — 8 bytes per thermocouple:
 * Byte 0-1: Thermocouple temperature (int16, °C × 10)
 * Byte 2-3: Cold junction temperature (int16, °C × 10)
 * Byte 4-5: PCB temperature          (int16, °C × 10)
 * Byte 6:   Fault register
 * Byte 7:   Reserved
 */

void CAN_SendTemperature(uint16_t can_id,
                         float tc_temp,
                         float cj_temp,
                         float pcb_temp,
                         uint8_t fault);

#endif /* CAN_NODE_H */

