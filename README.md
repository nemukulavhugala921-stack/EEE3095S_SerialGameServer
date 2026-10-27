# EEE3095S Serial Game Server (Tic-Tac-Toe)

An authoritative embedded game server implemented on an STM32F051 development board with a thin PC-side Python GUI client.

## Repository Structure

- `report/`: Compiled final technical project report PDF (`EEE3095S_Project_Report_NMKVHU004_MNYUMU003.pdf`).
- `embedded/`: STM32CubeIDE firmware project source code (C / HAL).
- `client/`: Thin PC-side GUI client (`gui.py`) and serial transport library (`serial_client.py`).
- `tests/`: Automated unit, integration, and protocol framing test harness (`pytest`).

## Protocol Summary
- **Physical Link:** ST-Link USB Virtual COM Port (115200 8N1)
- **Framing:** Plain ASCII, newline-terminated (`\n` or `\r\n`), max 64 bytes
- **Core Commands:** `CONNECT`, `NEW`, `MOVE:<0-8>`, `STATE`, `RESIGN`, `DISCONNECT`

## Demonstration Video
A video demonstration of the working system is available on YouTube:
- [System Demonstration Video](https://youtu.be/fJ0v8J7msK4)
