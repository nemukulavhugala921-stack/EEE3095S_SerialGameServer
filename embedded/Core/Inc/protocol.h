#ifndef PROTOCOL_H
#define PROTOCOL_H

#include "main.h"
#include <stdint.h>
#include <stdbool.h>

/* ====================================================================
 * Protocol Constants & Sizing (Frozen Protocol Contract)
 * ==================================================================== */
#define PROTOCOL_RING_BUFFER_SIZE 128  /* Interrupt circular queue capacity */
#define PROTOCOL_MAX_FRAME_LEN    64   /* Max characters per command frame including \n */

/* ====================================================================
 * Public API Functions
 * ==================================================================== */

/**
 * @brief Initialize protocol driver and start interrupt-driven UART reception.
 * @param huart Pointer to the UART hardware handle (e.g., &huart1).
 */
void protocol_init(UART_HandleTypeDef *huart);

/**
 * @brief Must be called from HAL_UART_RxCpltCallback when a byte arrives.
 */
void protocol_rx_isr(void);

/**
 * @brief Must be called from HAL_UART_ErrorCallback to recover from framing/overrun noise.
 */
void protocol_error_isr(void);

/**
 * @brief Non-blocking poll routine called inside main while(1) loop.
 *        Assembles incoming bytes into frames and dispatches commands on \n.
 */
void protocol_poll(void);

/**
 * @brief Send a newline-terminated ASCII string over UART to the host PC.
 * @param response Null-terminated C string (e.g., "OK\n").
 */
void protocol_send(const char *response);

#endif /* PROTOCOL_H */
