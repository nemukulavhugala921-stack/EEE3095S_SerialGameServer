#ifndef HARDWARE_H
#define HARDWARE_H

#include "main.h"
#include <stdint.h>
#include <stdbool.h>

/* ====================================================================
 * Public Hardware API
 * ==================================================================== */

/**
 * @brief Initialize hardware peripherals (LED states, debounce timers).
 */
void hardware_init(void);

/**
 * @brief Main periodic hardware task.
 *        Called non-blocking inside while(1) loop.
 *        - Scans and debounces physical reset button (SW0 on PA0).
 *        - Drives game status LEDs:
 *            IDLE:        Red OFF, Green OFF
 *            IN_PROGRESS: Red ON (Player X turn) or Green ON (Player O turn)
 *            GAME_OVER:   5 Hz blinking indicator (Red for X, Green for O, both for Draw)
 */
void hardware_update(void);

/**
 * @brief Pulse/toggle data activity LED (D0 on PB0) when serial data arrives.
 */
void hardware_indicate_activity(void);

#endif /* HARDWARE_H */
