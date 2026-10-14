#include "protocol.h"
#include "game.h"
#include <string.h>
#include <stdbool.h>

/* ====================================================================
 * Private Variables & State
 * ==================================================================== */
static UART_HandleTypeDef *g_huart = NULL;

/* 1-byte buffer for the hardware interrupt to write into */
static uint8_t g_rx_isr_byte = 0;

/* Circular Ring Buffer */
static volatile uint8_t  g_ring_buf[PROTOCOL_RING_BUFFER_SIZE];
static volatile uint16_t g_ring_head = 0;
static volatile uint16_t g_ring_tail = 0;

/* Line assembly buffer */
static char g_frame_buf[PROTOCOL_MAX_FRAME_LEN + 1];
static uint16_t g_frame_len = 0;
static bool g_frame_overflow = false;

/* ====================================================================
 * Private Function Prototypes
 * ==================================================================== */
static void protocol_dispatch_command(const char *cmd);

/* ====================================================================
 * Public API Implementation
 * ==================================================================== */

void protocol_init(UART_HandleTypeDef *huart)
{
    g_huart = huart;
    g_ring_head = 0;
    g_ring_tail = 0;
    g_frame_len = 0;
    g_frame_overflow = false;

    /* Initialize game engine state */
    game_init();

    /* Start interrupt-driven reception for 1 byte */
    if (g_huart != NULL)
    {
        HAL_UART_Receive_IT(g_huart, &g_rx_isr_byte, 1);
    }
}

void protocol_rx_isr(void)
{
    if (g_huart == NULL) return;

    /* Push byte to circular ring buffer */
    uint16_t next_head = (uint16_t)((g_ring_head + 1) % PROTOCOL_RING_BUFFER_SIZE);

    /* If queue is not full, store the byte (prevents tail overwrite) */
    if (next_head != g_ring_tail)
    {
        g_ring_buf[g_ring_head] = g_rx_isr_byte;
        g_ring_head = next_head;
    }

    /* Re-arm interrupt for the next byte */
    HAL_UART_Receive_IT(g_huart, &g_rx_isr_byte, 1);
}

void protocol_error_isr(void)
{
    if (g_huart == NULL) return;

    /* Clear common UART error flags (Overrun, Framing, Noise) */
    __HAL_UART_CLEAR_OREFLAG(g_huart);
    __HAL_UART_CLEAR_FEFLAG(g_huart);
    __HAL_UART_CLEAR_NEFLAG(g_huart);

    /* Re-arm interrupt so UART never locks up on bus noise */
    HAL_UART_Receive_IT(g_huart, &g_rx_isr_byte, 1);
}

void protocol_send(const char *response)
{
    if (g_huart != NULL && response != NULL)
    {
        HAL_UART_Transmit(g_huart, (uint8_t *)response, (uint16_t)strlen(response), 200);
    }
}

void protocol_poll(void)
{
    /* Process all bytes currently waiting in the circular ring buffer */
    while (g_ring_tail != g_ring_head)
    {
        uint8_t c = g_ring_buf[g_ring_tail];
        g_ring_tail = (uint16_t)((g_ring_tail + 1) % PROTOCOL_RING_BUFFER_SIZE);

        /* Carriage returns (\r) are discarded */
        if (c == '\r')
        {
            continue;
        }

        /* End-of-frame delimiter: newline (\n) */
        if (c == '\n')
        {
            if (g_frame_overflow)
            {
                /* Frame exceeded 64 bytes: reject and reset */
                g_frame_overflow = false;
                g_frame_len = 0;
                protocol_send("NACK:BADCMD\n");
            }
            else if (g_frame_len > 0)
            {
                /* Complete valid line received: null-terminate and dispatch */
                g_frame_buf[g_frame_len] = '\0';
                protocol_dispatch_command(g_frame_buf);
                g_frame_len = 0;
            }
            /* (If g_frame_len == 0, it was just a blank line, safely ignored) */
            continue;
        }

        /* Regular character */
        if (!g_frame_overflow)
        {
            if (g_frame_len < PROTOCOL_MAX_FRAME_LEN)
            {
                g_frame_buf[g_frame_len++] = (char)c;
            }
            else
            {
                /* Exceeded max allowed frame length (64 bytes) */
                g_frame_overflow = true;
            }
        }
    }
}

/* ====================================================================
 * Command Dispatcher
 * ==================================================================== */

static void protocol_dispatch_command(const char *cmd)
{
    char resp[PROTOCOL_MAX_FRAME_LEN + 1];

    if (strcmp(cmd, "CONNECT") == 0)
    {
        game_process_connect(resp, sizeof(resp));
        protocol_send(resp);
        return;
    }

    if (strcmp(cmd, "DISCONNECT") == 0)
    {
        game_process_disconnect(resp, sizeof(resp));
        protocol_send(resp);
        return;
    }

    if (strcmp(cmd, "NEW") == 0)
    {
        game_process_new(resp, sizeof(resp));
        protocol_send(resp);
        return;
    }

    if (strcmp(cmd, "STATE") == 0)
    {
        game_process_state(resp, sizeof(resp));
        protocol_send(resp);
        return;
    }

    if (strcmp(cmd, "RESIGN") == 0)
    {
        game_process_resign(resp, sizeof(resp));
        protocol_send(resp);
        return;
    }

    if (strncmp(cmd, "MOVE:", 5) == 0)
    {
        game_process_move(cmd + 5, resp, sizeof(resp));
        protocol_send(resp);
        return;
    }

    /* Unrecognized or malformed command */
    protocol_send("NACK:BADCMD\n");
}
