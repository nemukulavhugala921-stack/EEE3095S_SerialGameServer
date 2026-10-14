#include "game.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ctype.h>

/* ====================================================================
 * Private State & Constants
 * ==================================================================== */
static char g_board[10];           /* 9 cells + null terminator */
static char g_current_player = 'X';
static GameState g_state = GAME_STATE_IDLE;

/* 8 Winning Combinations (Rows, Columns, Diagonals) */
static const uint8_t WIN_COMBOS[8][3] = {
    {0, 1, 2}, /* Row 0 */
    {3, 4, 5}, /* Row 1 */
    {6, 7, 8}, /* Row 2 */
    {0, 3, 6}, /* Col 0 */
    {1, 4, 7}, /* Col 1 */
    {2, 5, 8}, /* Col 2 */
    {0, 4, 8}, /* Diagonal \ */
    {2, 4, 6}  /* Diagonal / */
};

/* ====================================================================
 * Private Helper Functions
 * ==================================================================== */

static bool check_win(char player)
{
    for (int i = 0; i < 8; i++)
    {
        if (g_board[WIN_COMBOS[i][0]] == player &&
            g_board[WIN_COMBOS[i][1]] == player &&
            g_board[WIN_COMBOS[i][2]] == player)
        {
            return true;
        }
    }
    return false;
}

static bool check_board_full(void)
{
    for (int i = 0; i < 9; i++)
    {
        if (g_board[i] == '.')
        {
            return false;
        }
    }
    return true;
}

/* ====================================================================
 * Public API Implementation
 * ==================================================================== */

void game_init(void)
{
    memset(g_board, '.', 9);
    g_board[9] = '\0';
    g_current_player = 'X';
    g_state = GAME_STATE_IDLE;
}

GameState game_get_state(void)
{
    return g_state;
}

char game_get_current_player(void)
{
    return g_current_player;
}

void game_get_board_string(char *out_board)
{
    if (out_board != NULL)
    {
        memcpy(out_board, g_board, 10);
    }
}

void game_process_connect(char *response_buf, size_t max_len)
{
    game_init();
    snprintf(response_buf, max_len, "OK\n");
}

void game_process_disconnect(char *response_buf, size_t max_len)
{
    game_init();
    snprintf(response_buf, max_len, "OK\n");
}

void game_process_new(char *response_buf, size_t max_len)
{
    /* Cannot start a NEW game while one is already in progress */
    if (g_state == GAME_STATE_IN_PROGRESS)
    {
        snprintf(response_buf, max_len, "NACK:BADCMD\n");
        return;
    }

    memset(g_board, '.', 9);
    g_board[9] = '\0';
    g_current_player = 'X';
    g_state = GAME_STATE_IN_PROGRESS;

    snprintf(response_buf, max_len, "OK:BOARD:.........\n");
}

void game_process_state(char *response_buf, size_t max_len)
{
    snprintf(response_buf, max_len, "BOARD:%s\n", g_board);
}

void game_process_resign(char *response_buf, size_t max_len)
{
    if (g_state != GAME_STATE_IN_PROGRESS)
    {
        snprintf(response_buf, max_len, "NACK:NOGAME\n");
        return;
    }

    g_state = GAME_STATE_GAME_OVER;
    snprintf(response_buf, max_len, "OK:GAMEOVER\n");
}

void game_process_move(const char *payload, char *response_buf, size_t max_len)
{
    if (payload == NULL)
    {
        snprintf(response_buf, max_len, "NACK:BADCMD\n");
        return;
    }

    /* Expected format: <player>:<index> (e.g. "X:4" or "O:0") */
    const char *colon = strchr(payload, ':');
    if (colon == NULL || colon != payload + 1)
    {
        snprintf(response_buf, max_len, "NACK:BADCMD\n");
        return;
    }

    char player = payload[0];
    if (player != 'X' && player != 'O')
    {
        snprintf(response_buf, max_len, "NACK:BADCMD\n");
        return;
    }

    /* Moves only valid when game is actively in progress */
    if (g_state != GAME_STATE_IN_PROGRESS)
    {
        snprintf(response_buf, max_len, "NACK:NOGAME\n");
        return;
    }

    /* Index parsing and validation */
    const char *idx_str = colon + 1;
    if (*idx_str == '\0')
    {
        snprintf(response_buf, max_len, "NACK:RANGE\n");
        return;
    }

    /* Verify all remaining characters are digits */
    for (const char *p = idx_str; *p != '\0'; p++)
    {
        if (!isdigit((unsigned char)*p))
        {
            snprintf(response_buf, max_len, "NACK:RANGE\n");
            return;
        }
    }

    char *endptr;
    long idx = strtol(idx_str, &endptr, 10);
    if (*endptr != '\0' || idx < 0 || idx > 8)
    {
        snprintf(response_buf, max_len, "NACK:RANGE\n");
        return;
    }

    /* Strict turn validation (proof of server authority) */
    if (player != g_current_player)
    {
        snprintf(response_buf, max_len, "NACK:NOTURN\n");
        return;
    }

    /* Occupied cell validation */
    if (g_board[idx] != '.')
    {
        snprintf(response_buf, max_len, "NACK:OCCUPIED\n");
        return;
    }

    /* Apply legal move */
    g_board[idx] = player;

    /* Check terminal win condition */
    if (check_win(player))
    {
        g_state = GAME_STATE_GAME_OVER;
        snprintf(response_buf, max_len, "WIN:%c\n", player);
        return;
    }

    /* Check terminal draw condition (full board, no winner) */
    if (check_board_full())
    {
        g_state = GAME_STATE_GAME_OVER;
        snprintf(response_buf, max_len, "DRAW\n");
        return;
    }

    /* Game continues: switch turn to the other player */
    g_current_player = (player == 'X') ? 'O' : 'X';
    snprintf(response_buf, max_len, "OK:BOARD:%s\n", g_board);
}
