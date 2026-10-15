#include "hardware.h"
#include "game.h"

/* ====================================================================
 * Button Debounce Configuration & State
 * ==================================================================== */
#define BUTTON_DEBOUNCE_MS 50

static GPIO_PinState g_btn_last_raw = GPIO_PIN_SET;
static GPIO_PinState g_btn_stable   = GPIO_PIN_SET;
static uint32_t      g_btn_last_time = 0;

/* ====================================================================
 * Public API Implementation
 * ==================================================================== */

void hardware_init(void)
{
    /* Ensure all indicator LEDs start in the OFF state */
    HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin | UCT_LED_GREEN_Pin | UCT_LED_D0_Pin, GPIO_PIN_RESET);

    g_btn_last_raw  = GPIO_PIN_SET;
    g_btn_stable    = GPIO_PIN_SET;
    g_btn_last_time = HAL_GetTick();
}

void hardware_indicate_activity(void)
{
    /* Toggle D0 LED on UART packet activity */
    HAL_GPIO_TogglePin(GPIOB, UCT_LED_D0_Pin);
}

void hardware_update(void)
{
    uint32_t now = HAL_GetTick();

    /* ----------------------------------------------------------------
     * 1. Debounce and Process User Push Button (SW0 on PA0)
     * ---------------------------------------------------------------- */
    GPIO_PinState current_raw = HAL_GPIO_ReadPin(GPIOA, UCT_SW0_Pin);

    if (current_raw != g_btn_last_raw)
    {
        /* State changed, restart debounce timer */
        g_btn_last_time = now;
        g_btn_last_raw = current_raw;
    }

    if ((now - g_btn_last_time) >= BUTTON_DEBOUNCE_MS)
    {
        if (current_raw != g_btn_stable)
        {
            g_btn_stable = current_raw;

            /* Falling edge: Button pressed (Active Low) */
            if (g_btn_stable == GPIO_PIN_RESET)
            {
                /* Physical button reset: locally resets game to IDLE */
                game_init();
                HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin | UCT_LED_GREEN_Pin, GPIO_PIN_RESET);
            }
        }
    }

    /* ----------------------------------------------------------------
     * 2. Drive Game Status LEDs (PB10 Red & PB11 Green)
     * ---------------------------------------------------------------- */
    GameState state = game_get_state();

    if (state == GAME_STATE_IDLE)
    {
        /* Both LEDs OFF when waiting for a game */
        HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin | UCT_LED_GREEN_Pin, GPIO_PIN_RESET);
    }
    else if (state == GAME_STATE_IN_PROGRESS)
    {
        /* Solid indication of active turn */
        char turn = game_get_current_player();
        if (turn == 'X')
        {
            HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin, GPIO_PIN_SET);
            HAL_GPIO_WritePin(GPIOB, UCT_LED_GREEN_Pin, GPIO_PIN_RESET);
        }
        else /* turn == 'O' */
        {
            HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOB, UCT_LED_GREEN_Pin, GPIO_PIN_SET);
        }
    }
    else if (state == GAME_STATE_GAME_OVER)
    {
        /* Rapid 5 Hz blinking (toggle every 100 ms) */
        bool blink_on = ((now / 100) % 2) == 0;
        char winner = game_get_winner();

        if (winner == 'X')
        {
            /* Red blinks for Player X victory */
            HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin, blink_on ? GPIO_PIN_SET : GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOB, UCT_LED_GREEN_Pin, GPIO_PIN_RESET);
        }
        else if (winner == 'O')
        {
            /* Green blinks for Player O victory */
            HAL_GPIO_WritePin(GPIOB, UCT_LED_GREEN_Pin, blink_on ? GPIO_PIN_SET : GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin, GPIO_PIN_RESET);
        }
        else /* Draw */
        {
            /* Both LEDs blink together for a draw */
            GPIO_PinState pin_state = blink_on ? GPIO_PIN_SET : GPIO_PIN_RESET;
            HAL_GPIO_WritePin(GPIOB, UCT_LED_RED_Pin | UCT_LED_GREEN_Pin, pin_state);
        }
    }
}
