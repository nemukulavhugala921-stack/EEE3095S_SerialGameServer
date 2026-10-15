# STM32 Server Finite State Machine (FSM)

## Overview
The embedded firmware implements an authoritative game server using a 3-state Finite State Machine (FSM). The state machine is evaluated in `embedded/Core/Src/game.c` and driven by commands received over the serial interface (`protocol.c`) and physical inputs (`hardware.c`).

---

## State Transition Diagram (Mermaid)

```mermaid
stateDiagram-v2
    [*] --> IDLE : Power On / System Reset

    state IDLE {
        description: Board empty ("........."), LEDs OFF, Waiting for game start
    }

    state IN_PROGRESS {
        description: Active match, Turn validation (X / O), LED indicates current player
    }

    state GAME_OVER {
        description: Match finished (Win / Draw), 5 Hz LED blinker active
    }

    IDLE --> IDLE : CONNECT -> OK\nSTATE -> BOARD:.........\nDISCONNECT -> OK
    IDLE --> IDLE : MOVE -> NACK:NOGAME\nRESIGN -> NACK:NOGAME

    IDLE --> IN_PROGRESS : NEW -> OK:BOARD:.........\n(Reset board, Player = X)

    IN_PROGRESS --> IN_PROGRESS : Valid MOVE (no 3-in-row, moves < 9)\n-> OK:BOARD:<grid>\n(Turn alternates X <-> O)
    IN_PROGRESS --> IN_PROGRESS : Invalid MOVE\n(NACK:NOTURN, NACK:OCCUPIED, NACK:RANGE)
    IN_PROGRESS --> IN_PROGRESS : STATE -> BOARD:<grid>\nCONNECT -> OK

    IN_PROGRESS --> GAME_OVER : Valid MOVE (3-in-a-row detected)\n-> WIN:<X|O>\n(Winner LED blinks at 5 Hz)
    IN_PROGRESS --> GAME_OVER : Valid MOVE (9 cells filled, no winner)\n-> DRAW\n(Both LEDs blink at 5 Hz)
    IN_PROGRESS --> GAME_OVER : RESIGN -> OK:WIN:<opponent>

    GAME_OVER --> GAME_OVER : STATE -> WIN:<winner> or DRAW\nMOVE -> NACK:NOGAME\nCONNECT -> OK
    GAME_OVER --> IN_PROGRESS : NEW -> OK:BOARD:.........\n(Reset board, Player = X)

    IN_PROGRESS --> IDLE : SW0 Pressed (PA0 Low)\nLocal Reset
    GAME_OVER --> IDLE : SW0 Pressed (PA0 Low)\nLocal Reset
    IDLE --> IDLE : SW0 Pressed (PA0 Low)\nNo change
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
  * `RESIGN` $\rightarrow$ `OK:WIN:<opponent>` (transitions to `GAME_OVER`)

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
  * Hardware button `SW0` $\rightarrow$ transitions to `IDLE`
