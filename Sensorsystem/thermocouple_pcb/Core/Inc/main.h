/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.h
  * @brief          : Header for main.c file.
  *                   This file contains the common defines of the application.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32g0xx_hal.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
/* USER CODE BEGIN Private defines */

/* NOTE: 50 MHz crystal (ABM10W-50.0000MHZ) is present on PCB but not used.
 * HSE oscillator on STM32G0B1 is rated for crystals up to ~48 MHz.
 * FDCAN uses HSI at 16 MHz running at 500 kbps instead.
 * Do not enable HSE without verifying crystal startup reliability first. */

/* MAX31856 register addresses */
#define MAX31856_CR0_REG    0x00
#define MAX31856_CR1_REG    0x01
#define MAX31856_FAULT_REG  0x0F

/* MAX31856 thermocouple types */
#define MAX31856_TC_TYPE_B  0x00
#define MAX31856_TC_TYPE_E  0x01
#define MAX31856_TC_TYPE_J  0x02
#define MAX31856_TC_TYPE_K  0x03
#define MAX31856_TC_TYPE_N  0x04
#define MAX31856_TC_TYPE_R  0x05
#define MAX31856_TC_TYPE_S  0x06
#define MAX31856_TC_TYPE_T  0x07

/* Chip select macros for two MAX31856 chips */
#define CS_T1_LOW()  HAL_GPIO_WritePin(CS_T1_GPIO_Port, CS_T1_Pin, GPIO_PIN_RESET)
#define CS_T1_HIGH() HAL_GPIO_WritePin(CS_T1_GPIO_Port, CS_T1_Pin, GPIO_PIN_SET)
#define CS_T2_LOW()  HAL_GPIO_WritePin(CS_T2_GPIO_Port, CS_T2_Pin, GPIO_PIN_RESET)
#define CS_T2_HIGH() HAL_GPIO_WritePin(CS_T2_GPIO_Port, CS_T2_Pin, GPIO_PIN_SET)

/* USER CODE END Private defines */
/* USER CODE END Includes */

/* Exported types ------------------------------------------------------------*/
/* USER CODE BEGIN ET */

/* USER CODE END ET */

/* Exported constants --------------------------------------------------------*/
/* USER CODE BEGIN EC */

/* USER CODE END EC */

/* Exported macro ------------------------------------------------------------*/
/* USER CODE BEGIN EM */

/* USER CODE END EM */

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN EFP */

/* USER CODE END EFP */

/* Private defines -----------------------------------------------------------*/
#define T1_DRDY_Pin GPIO_PIN_2
#define T1_DRDY_GPIO_Port GPIOD
#define T2_DRDY_Pin GPIO_PIN_3
#define T2_DRDY_GPIO_Port GPIOD
#define CS_T2_Pin GPIO_PIN_6
#define CS_T2_GPIO_Port GPIOB
#define CS_T1_Pin GPIO_PIN_7
#define CS_T1_GPIO_Port GPIOB
#define T1_FAULT_Pin GPIO_PIN_8
#define T1_FAULT_GPIO_Port GPIOB
#define T2_Fault_Pin GPIO_PIN_9
#define T2_Fault_GPIO_Port GPIOB

/* USER CODE BEGIN Private defines */

/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
