/*
 * max31856.c — Driver for the MAX31856 thermocouple-to-digital converter.
 *
 * SPI protocol (Mode 1: CPOL=0, CPHA=1, MSB first):
 *   Read:  pull CS low, send register address with bit7=0, read N bytes, pull CS high.
 *   Write: pull CS low, send register address with bit7=1, send data byte, pull CS high.
 *
 *  Created on: 27. apr. 2026
 *      Author: joaki
 */

#include "max31856.h"
#include "main.h"

extern SPI_HandleTypeDef hspi1;

/* Read one or more consecutive registers starting at startReg.
 * Bit 7 of the address is cleared (0 = read direction per MAX31856 protocol). */
static void SPI_ReadBytes(GPIO_TypeDef *cs_port,
                          uint16_t cs_pin,
                          uint8_t startReg,
                          uint8_t *buf,
                          uint16_t len)
{
    uint8_t addr = startReg & 0x7F;   /* ensure bit7=0 (read) */
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_RESET);  /* select chip */
    HAL_SPI_Transmit(&hspi1, &addr, 1, 100);             /* send register address */
    HAL_SPI_Receive(&hspi1, buf, len, 100);              /* read back data */
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_SET);    /* deselect chip */
}

/* Write a single byte to one register.
 * Bit 7 of the address is set (1 = write direction per MAX31856 protocol). */
void MAX31856_WriteRegister(GPIO_TypeDef *cs_port,
                            uint16_t cs_pin,
                            uint8_t reg,
                            uint8_t value)
{
    uint8_t tx[2];
    tx[0] = reg | 0x80;   /* set bit7=1 (write) */
    tx[1] = value;
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_RESET);  /* select chip */
    HAL_SPI_Transmit(&hspi1, tx, 2, 100);                /* send address + data */
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_SET);    /* deselect chip */
}

/* Initialise one MAX31856 chip:
 *  - CR0 = 0x80 → automatic (continuous) conversion mode
 *  - CR1 = TC_TYPE_N → linearisation for type-N thermocouple */
void MAX31856_Init(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_SET);  /* make sure CS starts high */
    HAL_Delay(50);

    /* Dummy read to wake up SPI — first transaction after power-up
     * can be lost otherwise, causing the Type N config write to fail */
    uint8_t dummy;
    SPI_ReadBytes(cs_port, cs_pin, 0x00, &dummy, 1);
    HAL_Delay(10);

    /* Write CR0 before CR1 as required by the MAX31856 datasheet */
    MAX31856_WriteRegister(cs_port, cs_pin, MAX31856_CR0_REG, 0x80);  /* auto-convert on */
    HAL_Delay(10);
    MAX31856_WriteRegister(cs_port, cs_pin, MAX31856_CR1_REG, MAX31856_TC_TYPE_N);
    HAL_Delay(10);
}

/* Read the linearised thermocouple temperature from registers 0x0C–0x0E (3 bytes).
 *
 * The chip stores the result as a 19-bit two's-complement value in the upper
 * 19 bits of those 3 bytes (bits 23..5).  Resolution is 2^-7 = 0.0078125 °C/LSB.
 *
 * Steps:
 *  1. Combine 3 bytes into a 24-bit integer.
 *  2. Shift right 5 to align the 19-bit value at bit 0.
 *  3. Sign-extend from bit 18 so negative temperatures work correctly.
 *  4. Multiply by the resolution constant to get °C. */
float MAX31856_ReadThermocouple(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    uint8_t b[3];
    SPI_ReadBytes(cs_port, cs_pin, 0x0C, b, 3);

    /* Assemble 24 bits from the three bytes */
    int32_t raw = ((int32_t)b[0] << 16) |
                  ((int32_t)b[1] << 8)  |
                  b[2];

    raw >>= 5;  /* discard the 5 unused lower bits → 19-bit value */

    /* Sign-extend: if bit 18 is set the temperature is negative */
    if (raw & (1 << 18))
        raw |= ~((1 << 19) - 1);

    return raw * 0.0078125f;  /* 1 LSB = 1/128 °C */
}

/* Read the cold-junction (on-chip ambient) temperature from registers 0x0A–0x0B (2 bytes).
 *
 * The chip stores a 14-bit two's-complement value in the upper 14 bits of those
 * 2 bytes (bits 15..2).  Resolution is 2^-6 = 0.015625 °C/LSB.
 *
 * Steps:
 *  1. Combine 2 bytes into a signed 16-bit integer.
 *  2. Arithmetic right-shift by 2 to discard the 2 unused lower bits.
 *     The sign bit propagates automatically because the type is int16_t.
 *  3. Multiply by the resolution constant to get °C. */
float MAX31856_ReadColdJunction(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    uint8_t b[2];
    SPI_ReadBytes(cs_port, cs_pin, 0x0A, b, 2);

    int16_t raw = (int16_t)((b[0] << 8) | b[1]);
    raw >>= 2;  /* discard 2 unused lower bits; sign extends automatically */

    return raw * 0.015625f;  /* 1 LSB = 1/64 °C */
}

/* Read the fault status register (0x0F).
 * Each bit flags a different fault condition (open circuit, over/under-range, etc.).
 * A value of 0x00 means no faults. */
uint8_t MAX31856_ReadFault(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    uint8_t fault;
    SPI_ReadBytes(cs_port, cs_pin, 0x0F, &fault, 1);
    return fault;
}
