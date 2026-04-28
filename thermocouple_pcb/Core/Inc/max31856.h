/*
 * max31856.h — Driver for the MAX31856 thermocouple-to-digital converter.
 *
 * The MAX31856 communicates over SPI (Mode 1: CPOL=0, CPHA=1).
 * Each chip has its own chip-select (CS) line; all chips share the same SPI bus.
 *
 *  Created on: 27. apr. 2026
 *      Author: joaki
 */

#ifndef MAX31856_H
#define MAX31856_H

#include "stm32g0xx_hal.h"

/* Write one byte to a MAX31856 register over SPI. */
void MAX31856_WriteRegister(GPIO_TypeDef *cs_port,
                            uint16_t cs_pin,
                            uint8_t reg,
                            uint8_t value);

/* Configure the chip: enable auto-conversion mode and select thermocouple type N. */
void MAX31856_Init(GPIO_TypeDef *cs_port, uint16_t cs_pin);

/* Read the linearised thermocouple temperature in °C (19-bit signed, 0.0078125 °C/LSB). */
float MAX31856_ReadThermocouple(GPIO_TypeDef *cs_port, uint16_t cs_pin);

/* Read the cold-junction (on-chip) temperature in °C (14-bit signed, 0.015625 °C/LSB). */
float MAX31856_ReadColdJunction(GPIO_TypeDef *cs_port, uint16_t cs_pin);

/* Read the fault status register (bit flags defined in the MAX31856 datasheet). */
uint8_t MAX31856_ReadFault(GPIO_TypeDef *cs_port, uint16_t cs_pin);

#endif /* MAX31856_H */
