/*
 * can_node.c — CAN bus transmission for thermocouple sensor data.
 *
 * Uses classic CAN (not FD) at 500 kbps via the STM32G0B1 FDCAN peripheral.
 * HSI at 16 MHz → prescaler 1 × (1 + 23 + 8) time quanta = 500 kbps.
 *
 *  Created on: 27. apr. 2026
 *      Author: joakim
 */

#include "can_node.h"
#include "main.h"

extern FDCAN_HandleTypeDef hfdcan1;

/* Build and transmit one 8-byte CAN frame with temperature and fault data.
 *
 * Temperatures are floats in °C; they are scaled by CAN_TEMP_SCALE (×10) and
 * stored as signed 16-bit integers so one LSB = 0.1 °C.  The three values are
 * packed big-endian (high byte first) into the 8-byte payload:
 *
 *   Byte 0-1: thermocouple temperature  (int16, °C × 10)
 *   Byte 2-3: cold-junction temperature (int16, °C × 10)
 *   Byte 4-5: PCB temperature           (int16, °C × 10)
 *   Byte 6:   MAX31856 fault register
 *   Byte 7:   reserved (0x00)
 */
void CAN_SendTemperature(uint16_t can_id,
                         float tc_temp,
                         float cj_temp,
                         float pcb_temp,
                         uint8_t fault)
{
    FDCAN_TxHeaderTypeDef TxHeader;
    uint8_t TxData[8] = {0};

    /* Convert float °C → int16 (°C × 10) to avoid sending floats over CAN */
    int16_t tc  = (int16_t)(tc_temp  * CAN_TEMP_SCALE);
    int16_t cj  = (int16_t)(cj_temp  * CAN_TEMP_SCALE);
    int16_t pcb = (int16_t)(pcb_temp * CAN_TEMP_SCALE);

    /* Pack big-endian: high byte at lower index so any CAN receiver can decode
     * without needing to know the MCU's native endianness */
    TxData[0] = (uint8_t)(tc  >> 8);
    TxData[1] = (uint8_t)(tc  & 0xFF);
    TxData[2] = (uint8_t)(cj  >> 8);
    TxData[3] = (uint8_t)(cj  & 0xFF);
    TxData[4] = (uint8_t)(pcb >> 8);
    TxData[5] = (uint8_t)(pcb & 0xFF);
    TxData[6] = fault;   /* raw fault byte from MAX31856 register 0x0F */
    TxData[7] = 0x00;    /* reserved for future use */

    /* Standard 11-bit CAN ID, classic frame (not FD), 8 data bytes */
    TxHeader.Identifier          = can_id;
    TxHeader.IdType              = FDCAN_STANDARD_ID;
    TxHeader.TxFrameType         = FDCAN_DATA_FRAME;
    TxHeader.DataLength          = FDCAN_DLC_BYTES_8;
    TxHeader.ErrorStateIndicator = FDCAN_ESI_ACTIVE;
    TxHeader.BitRateSwitch       = FDCAN_BRS_OFF;   /* no bit-rate switch (classic CAN) */
    TxHeader.FDFormat            = FDCAN_CLASSIC_CAN;
    TxHeader.TxEventFifoControl  = FDCAN_NO_TX_EVENTS;
    TxHeader.MessageMarker       = 0;

    /* Place the message in the TX FIFO; the peripheral sends it automatically */
    HAL_FDCAN_AddMessageToTxFifoQ(&hfdcan1, &TxHeader, TxData);
}

/* HAL callback: clock and GPIO setup for FDCAN1 (called by HAL_FDCAN_Init).
 * PA11 = FDCAN1_RX, PA12 = FDCAN1_TX, alternate function 9. */
void HAL_FDCAN_MspInit(FDCAN_HandleTypeDef* fdcanHandle)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    if(fdcanHandle->Instance == FDCAN1)
    {
        __HAL_RCC_FDCAN_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();

        /* PA11 = FDCAN1_RX, PA12 = FDCAN1_TX */
        GPIO_InitStruct.Pin       = GPIO_PIN_11 | GPIO_PIN_12;
        GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
        GPIO_InitStruct.Pull      = GPIO_NOPULL;
        GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
        GPIO_InitStruct.Alternate = GPIO_AF9_FDCAN1;
        HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

        /* Enable both FDCAN interrupt lines at highest priority */
        HAL_NVIC_SetPriority(FDCAN1_IT0_IRQn, 0, 0);
        HAL_NVIC_EnableIRQ(FDCAN1_IT0_IRQn);
        HAL_NVIC_SetPriority(FDCAN1_IT1_IRQn, 0, 0);
        HAL_NVIC_EnableIRQ(FDCAN1_IT1_IRQn);
    }
}

/* HAL callback: undo everything done in MspInit (called on de-initialisation). */
void HAL_FDCAN_MspDeInit(FDCAN_HandleTypeDef* fdcanHandle)
{
    if(fdcanHandle->Instance == FDCAN1)
    {
        __HAL_RCC_FDCAN_CLK_DISABLE();
        HAL_GPIO_DeInit(GPIOA, GPIO_PIN_11 | GPIO_PIN_12);
        HAL_NVIC_DisableIRQ(FDCAN1_IT0_IRQn);
        HAL_NVIC_DisableIRQ(FDCAN1_IT1_IRQn);
    }
}
