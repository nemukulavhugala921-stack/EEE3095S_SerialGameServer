# STM32 Server Finite State Machine (FSM)

## Overview
The embedded firmware implements an authoritative game server using a 3-state Finite State Machine (FSM). The state machine is evaluated in `embedded/Core/Src/game.c` and driven by commands received over the serial interface (`protocol.c`) and physical inputs (`hardware.c`).

---

## State Transition Diagram (Mermaid)

```mermaid
stateDiagram-v2
    [*] --> IDLE : Power On / MCU Hardware Reset

    state IDLE {
        description: Board empty ("........."), LEDs OFF, Waiting for game start
    }

    state IN_PROGRESS {
        description: Active match, Turn validation (X / O), LED indicates active turn
    }

    state GAME_OVER {
        description: Match finished (Win / Draw), 5 Hz LED blinker active
    }

    %% Self loops on IDLE
    IDLE --> IDLE : CONNECT -> OK\nSTATE -> BOARD:.........\nDISCONNECT -> OK
    IDLE --> IDLE : MOVE / RESIGN -> NACK:NOGAME

    %% Forward transition to active match
    IDLE --> IN_PROGRESS : NEW -> OK:BOARD:.........\n(Init board, Player = X)

    %% In-Progress operations
    IN_PROGRESS --> IN_PROGRESS : Valid MOVE [no win] -> OK:BOARD:<grid>\n(Turn alternates X <-> O)
    IN_PROGRESS --> IN_PROGRESS : Invalid MOVE -> NACK:NOTURN | NACK:OCCUPIED | NACK:RANGE
    IN_PROGRESS --> IN_PROGRESS : STATE -> BOARD:<grid>\nNEW -> NACK:BADCMD

    %% Terminal transitions to GAME_OVER
    IN_PROGRESS --> GAME_OVER : MOVE [win detected] -> WIN:<X|O>\n(Winner LED blinks at 5 Hz)
    IN_PROGRESS --> GAME_OVER : MOVE [9 cells filled, no win] -> DRAW\n(Both LEDs blink at 5 Hz)
    IN_PROGRESS --> GAME_OVER : RESIGN -> OK:GAMEOVER

    %% Game Over operations
    GAME_OVER --> GAME_OVER : STATE -> BOARD:<grid>\nMOVE / RESIGN -> NACK:NOGAME
    GAME_OVER --> IN_PROGRESS : NEW -> OK:BOARD:.........\n(Replay: Reset board, Player = X)

    %% Resets returning to IDLE
    IN_PROGRESS --> IDLE : SW0 Button Press (PA0)\nCONNECT -> OK\nDISCONNECT -> OK
    GAME_OVER --> IDLE : SW0 Button Press (PA0)\nCONNECT -> OK\nDISCONNECT -> OK
```

---

## State Specifications

### 1. `GAME_STATE_IDLE`
* **Entry Condition:** Microcontroller boot, hardware button `SW0` reset, or game re-initialization.
* **Internal State:**
  * Board array: `g_board = "........."` (9 empty cells).
  * Current player: `X`.
  * Winner: None (`'\0'`).
  * Move counter: `0`.
* **Hardware Output:**
  * Red LED (`PB10`) = **OFF**.
  * Green LED (`PB11`) = **OFF**.
* **Protocol Behavior:**
  * `CONNECT` $\rightarrow$ `OK`
  * `DISCONNECT` $\rightarrow$ `OK`
  * `STATE` $\rightarrow$ `BOARD:.........`
  * `NEW` $\rightarrow$ `OK:BOARD:.........` (transitions to `IN_PROGRESS`)
  * `MOVE:<player>:<index>` $\rightarrow$ `NACK:NOGAME`
  * `RESIGN` $\rightarrow$ `NACK:NOGAME`

---

### 2. `GAME_STATE_IN_PROGRESS`
* **Entry Condition:** Receipt of `NEW` command from client while in `IDLE` or `GAME_OVER`.
* **Internal State:**
  * Turn alternates between `'X'` and `'O'`.
  * Moves count increases on each valid square placement.
* **Hardware Output:**
  * Turn == `'X'`: Red LED (`PB10`) = **ON**, Green LED (`PB11`) = **OFF**.
  * Turn == `'O'`: Red LED (`PB10`) = **OFF**, Green LED (`PB11`) = **ON**.
* **Protocol Behavior:**
  * `MOVE:<player>:<index>`:
    * If `player != current_player` $\rightarrow$ `NACK:NOTURN`
    * If `index < 0 || index > 8` $\rightarrow$ `NACK:RANGE`
    * If `board[index] != '.'` $\rightarrow$ `NACK:OCCUPIED`
    * If move is valid and results in 3-in-a-row $\rightarrow$ `WIN:<player>` (transitions to `GAME_OVER`)
    * If move is valid and all 9 cells full without winner $\rightarrow$ `DRAW` (transitions to `GAME_OVER`)
    * If move is valid and game continues $\rightarrow$ `OK:BOARD:<grid>` (updates board, swaps turn)
  * `STATE` $\rightarrow$ `BOARD:<grid>`
  * `RESIGN` $\rightarrow$ `OK:GAMEOVER` (transitions to `GAME_OVER`)

---

### 3. `GAME_STATE_GAME_OVER`
* **Entry Condition:** Winning combination reached, 9 moves made without a win (draw), or player resignation.
* **Internal State:**
  * Winner stored (`'X'`, `'O'`, or `'='` for draw).
  * Board is frozen; no further moves accepted.
* **Hardware Output (5 Hz Blinker via non-blocking hardware tick):**
  * Winner `'X'`: Red LED (`PB10`) blinks at 5 Hz (100 ms ON / 100 ms OFF). Green is OFF.
  * Winner `'O'`: Green LED (`PB11`) blinks at 5 Hz (100 ms ON / 100 ms OFF). Red is OFF.
  * Draw `'='`: Both Red and Green LEDs blink simultaneously at 5 Hz.
* **Protocol Behavior:**
  * `MOVE:<player>:<index>` $\rightarrow$ `NACK:NOGAME`
  * `STATE` $\rightarrow$ `WIN:<winner>` or `DRAW`
  * `NEW` $\rightarrow$ `OK:BOARD:.........` (transitions to `IN_PROGRESS`)
  * `CONNECT` / `DISCONNECT` $\rightarrow$ `OK` (transitions to `IDLE`)
  * Hardware button `SW0` (active low on PA0) $\rightarrow$ transitions to `IDLE`
