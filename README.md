# EEE3095S Serial Game Server (Tic-Tac-Toe)

An authoritative embedded game server implemented on an STM32F051 development board with a thin PC-side Python GUI client.

## Repository Structure

- `embedded/`: STM32CubeIDE project source code (C / HAL).
- `client/`: Thin PC-side GUI client and serial communication library (Python).
- `tests/`: Automated test harness (pytest).
- `docs/`: Circuit diagram, Server FSM, GUI flowchart, and sequence diagrams.
- `report/`: IEEE Conference Format project report and source materials.

## Protocol Summary
- **Physical Link:** ST-Link USB Virtual COM Port (115200 8N1)
- **Framing:** Plain ASCII, newline-terminated (`\n` or `\r\n`), max 64 bytes
- **Core Commands:** `CONNECT`, `NEW`, `MOVE:<0-8>`, `STATE`, `RESIGN`, `DISCONNECT`
