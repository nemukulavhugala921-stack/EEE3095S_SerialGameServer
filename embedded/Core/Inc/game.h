#ifndef GAME_H
#define GAME_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* ====================================================================
 * Game States (Finite State Machine)
 * ==================================================================== */
typedef enum {
    GAME_STATE_IDLE = 0,
    GAME_STATE_IN_PROGRESS,
    GAME_STATE_GAME_OVER
} GameState;

/* ====================================================================
 * Public Game Engine API
 * ==================================================================== */

/**
 * @brief Initialize or reset the game engine to default IDLE state.
 */
void game_init(void);

/**
 * @brief Get the current FSM state.
 */
GameState game_get_state(void);

/**
 * @brief Get the player whose turn it currently is ('X' or 'O').
 */
char game_get_current_player(void);

/**
 * @brief Get the winner of the game ('X', 'O', 'D' for Draw, or '.' if none/idle).
 */
char game_get_winner(void);

/**
 * @brief Copy the current 9-character board string into out_board (at least 10 bytes).
 */
void game_get_board_string(char *out_board);

/**
 * @brief Process CONNECT command: resets session to IDLE.
 */
void game_process_connect(char *response_buf, size_t max_len);

/**
 * @brief Process DISCONNECT command: resets session to IDLE.
 */
void game_process_disconnect(char *response_buf, size_t max_len);

/**
 * @brief Process NEW command: starts a fresh game from IDLE or GAME_OVER.
 */
void game_process_new(char *response_buf, size_t max_len);

/**
 * @brief Process STATE command: returns current board snapshot.
 */
void game_process_state(char *response_buf, size_t max_len);

/**
 * @brief Process RESIGN command: active game forfeits to GAME_OVER.
 */
void game_process_resign(char *response_buf, size_t max_len);

/**
 * @brief Process MOVE command: validates and applies move for MOVE:<player>:<index>.
 * @param payload The argument string after "MOVE:" (e.g. "X:4" or "O:0").
 */
void game_process_move(const char *payload, char *response_buf, size_t max_len);

#endif /* GAME_H */
