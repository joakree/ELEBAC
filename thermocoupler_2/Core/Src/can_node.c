/*
 * can_node.c
 *
 *  Created on: 27. apr. 2026
 *      Author: joakim
 */


#include "can_node.h"

static FDCAN_TxHeaderTypeDef TxHeader;

void CAN_Node_Init(void)
{
    /* FDCAN1 configuration — 1 Mbps at 50 MHz HSE */
    hfdcan1.Instance                  = FDCAN1;
    hfdcan1.Init.FrameFormat          = FDCAN_FRAME_CLASSIC;
    hfdcan1.Init.Mode                 = FDCAN_MODE_NORMAL;
    hfdcan1.Init.AutoRetransmission   = ENABLE;
    hfdcan1.Init.TransmitPause        = DISABLE;
    hfdcan1.Init.ProtocolException    = DISABLE;

    /* Timing for 1 Mbps at 50 MHz HSE
     * Tq = 20 ns, Total = 50 Tq, Sample point = 76% */
    hfdcan1.Init.NominalPrescaler     = 1;
    hfdcan1.Init.NominalSyncJumpWidth = 1;
    hfdcan1.Init.NominalTimeSeg1      = 37;
    hfdcan1.Init.NominalTimeSeg2      = 12;

    /* Data phase (unused in classic CAN, set to minimum) */
    hfdcan1.Init.DataPrescaler        = 1;
    hfdcan1.Init.DataSyncJumpWidth    = 1;
    hfdcan1.Init.DataTimeSeg1         = 1;
    hfdcan1.Init.DataTimeSeg2         = 1;

    /* Message RAM configuration */
    hfdcan1.Init.MessageRAMOffset         = 0;
    hfdcan1.Init.StdFiltersNbr            = 0;
    hfdcan1.Init.ExtFiltersNbr            = 0;
    hfdcan1.Init.RxFifo0ElmtsNbr         = 8;
    hfdcan1.Init.RxFifo0ElmtSize         = FDCAN_DATA_BYTES_8;
    hfdcan1.Init.RxFifo1ElmtsNbr         = 0;
    hfdcan1.Init.RxFifo1ElmtSize         = FDCAN_DATA_BYTES_8;
    hfdcan1.Init.RxBuffersNbr             = 0;
    hfdcan1.Init.RxBufferSize             = FDCAN_DATA_BYTES_8;
    hfdcan1.Init.TxEventsNbr              = 0;
    hfdcan1.Init.TxBuffersNbr             = 0;
    hfdcan1.Init.TxFifoQueueElmtsNbr      = 4;
    hfdcan1.Init.TxFifoQueueMode          = FDCAN_TX_FIFO_OPERATION;
    hfdcan1.Init.TxElmtSize               = FDCAN_DATA_BYTES_8;

    if (HAL_FDCAN_Init(&hfdcan1) != HAL_OK)
    {
        Error_Handler();
    }

    /* Start FDCAN */
    if (HAL_FDCAN_Start(&hfdcan1) != HAL_OK)
    {
        Error_Handler();
    }

    /* Configure TX header — reused for all transmissions */
    TxHeader.Identifier          = CAN_ID_THERMOCOUPLE_NODE;
    TxHeader.IdType              = FDCAN_STANDARD_ID;
    TxHeader.TxFrameType         = FDCAN_DATA_FRAME;
    TxHeader.DataLength          = FDCAN_DLC_BYTES_8;
    TxHeader.ErrorStateIndicator = FDCAN_ESI_ACTIVE;
    TxHeader.BitRateSwitch       = FDCAN_BRS_OFF;
    TxHeader.FDFormat            = FDCAN_CLASSIC_CAN;
    TxHeader.TxEventFifoControl  = FDCAN_NO_TX_EVENTS;
    TxHeader.MessageMarker       = 0;
}

void CAN_Node_Transmit(float tc_temp, float cj_temp,
                       float pcb_temp, uint8_t fault)
{
    uint8_t TxData[8] = {0};

    /* Scale temperatures to int16 (°C × 10) */
    int16_t tc  = (int16_t)(tc_temp  * CAN_TEMP_SCALE);
    int16_t cj  = (int16_t)(cj_temp  * CAN_TEMP_SCALE);
    int16_t pcb = (int16_t)(pcb_temp * CAN_TEMP_SCALE);

    /* Pack into 8-byte CAN frame (big-endian) */
    TxData[0] = (uint8_t)(tc  >> 8);
    TxData[1] = (uint8_t)(tc  & 0xFF);
    TxData[2] = (uint8_t)(cj  >> 8);
    TxData[3] = (uint8_t)(cj  & 0xFF);
    TxData[4] = (uint8_t)(pcb >> 8);
    TxData[5] = (uint8_t)(pcb & 0xFF);
    TxData[6] = fault;
    TxData[7] = 0x00; /* Reserved */

    if (HAL_FDCAN_AddMessageToTxFifoQ(&hfdcan1,
                                       &TxHeader,
                                       TxData) != HAL_OK)
    {
        Error_Handler();
    }
}
