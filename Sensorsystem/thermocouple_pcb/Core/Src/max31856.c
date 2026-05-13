/*
 * max31856.c — Driver for the MAX31856 thermocouple-to-digital converter.
 *

 *  Created on: 27. apr. 2026
 *      Author: joaki
 */

#include "max31856.h"
#include "main.h"

extern SPI_HandleTypeDef hspi1;


static void SPI_ReadBytes(GPIO_TypeDef *cs_port,
                          uint16_t cs_pin,
                          uint8_t startReg,
                          uint8_t *buf,
                          uint16_t len)
{
    uint8_t addr = startReg & 0x7F;
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, &addr, 1, 100);
    HAL_SPI_Receive(&hspi1, buf, len, 100);
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_SET);
}

/* Write a single byte to one register. */
void MAX31856_WriteRegister(GPIO_TypeDef *cs_port,
                            uint16_t cs_pin,
                            uint8_t reg,
                            uint8_t value)
{
    uint8_t tx[2];
    tx[0] = reg | 0x80;
    tx[1] = value;
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_RESET);
    HAL_SPI_Transmit(&hspi1, tx, 2, 100);
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_SET);
}

void MAX31856_Init(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    HAL_GPIO_WritePin(cs_port, cs_pin, GPIO_PIN_SET);
    HAL_Delay(50);

    /* Dummy read to wake up SPI — first transaction after power-up
     * can be lost otherwise, causing the Type N config write to fail */
    uint8_t dummy;
    SPI_ReadBytes(cs_port, cs_pin, 0x00, &dummy, 1);
    HAL_Delay(10);

    MAX31856_WriteRegister(cs_port, cs_pin, MAX31856_CR0_REG, 0x80);  /* auto-convert on */
    HAL_Delay(10);
    MAX31856_WriteRegister(cs_port, cs_pin, MAX31856_CR1_REG, MAX31856_TC_TYPE_N);
    HAL_Delay(10);
}

/* Read the linearised thermocouple temperature from registers 0x0C–0x0E (3 bytes).
 *
 * The chip stores the result as a 19-bit two's-complement value in the upper */
float MAX31856_ReadThermocouple(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    uint8_t b[3];
    SPI_ReadBytes(cs_port, cs_pin, 0x0C, b, 3);

    /* Assemble 24 bits from the three bytes */
    int32_t raw = ((int32_t)b[0] << 16) |
                  ((int32_t)b[1] << 8)  |
                  b[2];

    raw >>= 5;

    /* Sign-extend: if bit 18 is set the temperature is negative */
    if (raw & (1 << 18))
        raw |= ~((1 << 19) - 1);

    return raw * 0.0078125f;  /* 1 LSB = 1/128 °C */
}

/* Read the cold-junction (on-chip ambient) temperature from registers 0x0A–0x0B (2 bytes).
 *. */
float MAX31856_ReadColdJunction(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    uint8_t b[2];
    SPI_ReadBytes(cs_port, cs_pin, 0x0A, b, 2);

    int16_t raw = (int16_t)((b[0] << 8) | b[1]);
    raw >>= 2;

    return raw * 0.015625f;  /* 1 LSB = 1/64 °C */
}

/* Read the fault status register (0x0F). */
uint8_t MAX31856_ReadFault(GPIO_TypeDef *cs_port, uint16_t cs_pin)
{
    uint8_t fault;
    SPI_ReadBytes(cs_port, cs_pin, 0x0F, &fault, 1);
    return fault;
}
