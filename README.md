# EEE3095S Serial Game Server (Tic-Tac-Toe)

An authoritative embedded game server implemented on an STM32F051 development board communicating with a thin PC-side Python GUI client over UART serial.

**Course:** EEE3095S Embedded Systems II CS Project 2026  
**Institution:** University of Cape Town (UCT), Department of Electrical Engineering  
**Authors:**  
- Nemukula Vhugala (`NMKVHU004`)  
- Munyai Umusindisi Cindy (`MNYUMU003`)  

**Key Links:**  
- 📄 **Project Report PDF:** [`report/EEE3095S_Project_Report_NMKVHU004_MNYUMU003.pdf`](report/EEE3095S_Project_Report_NMKVHU004_MNYUMU003.pdf)  
- 🎥 **YouTube Demonstration Video:** [https://youtu.be/fJ0v8J7msK4](https://youtu.be/fJ0v8J7msK4)  

---

## Repository Structure

```
EEE3096S_Project/
├── report/
│   └── EEE3095S_Project_Report_NMKVHU004_MNYUMU003.pdf # Final submission report PDF
├── embedded/                                           # Firmware project (STM32CubeIDE)
│   ├── Core/Inc/                                       # Headers (game logic, FSM, protocol, ring buffer)
│   ├── Core/Src/                                       # C Source files
│   ├── Drivers/                                        # STM32 HAL and CMSIS drivers
│   ├── SerialGameServer.ioc                            # CubeMX pinout & clock configuration
│   └── STM32F051R8TX_FLASH.ld                          # Linker script
├── client/                                             # Python PC-side thin client
│   ├── gui.py                                          # Tkinter graphical user interface
│   ├── serial_client.py                                # Serial transport & framing library
│   ├── mock_stm32.py                                   # Standalone mock TCP server for simulation
│   ├── test_day3_stm32.py                              # Automated 26-point hardware regression test
│   └── serial_monitor.py                               # Raw serial terminal monitor
├── tests/                                              # Automated test suite (pytest)
│   ├── test_server.py                                  # Core server command & rule tests
│   ├── test_gui_responses.py                           # GUI state machine & response parsing tests
│   ├── test_mock_server_framing.py                     # 64-byte framing & boundary condition tests
│   └── test_serial_client.py                           # Transport & banner handling tests
├── requirements.txt                                    # Python dependencies
└── README.md
```

---

## Prerequisites & Setup

### 1. Python Environment
- Python 3.10 or newer (Tkinter is included in standard Python installations on Windows/macOS).
- Install the required dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Embedded Toolchain (For Hardware Run)
- **STM32CubeIDE** (v1.12 or newer recommended).
- **Hardware:** STM32F0 Discovery board (or custom UCT EEE3095S board with STM32F051R8 MCU) and a Mini-USB cable.

---

## How to Run the Project

### Option A: Hardware Run (With Physical STM32 Board)

#### Step 1: Flash the STM32 Firmware
1. Connect the STM32 board to your PC using the USB ST-Link port.
2. Open **STM32CubeIDE**.
3. Select **File > Import... > General > Existing Projects into Workspace**.
4. Browse to and select the `embedded/` directory, then click **Finish**.
5. Build the project (**Project > Build Project** or `Ctrl+B`).
6. Flash the firmware onto the board (**Run > Run** or `Ctrl+F11`).
   - The ST-Link will enumerate as a Virtual COM Port (e.g., `COM3` on Windows, or `/dev/ttyACM0` on Linux).

#### Step 2: Launch the Python GUI Client
1. In your terminal, run:
   ```bash
   python client/gui.py
   ```
2. In the **Connection** text box at the top of the GUI:
   - Replace the default text `mock` with your board's COM port (e.g. `COM3` or `COM4`).
3. Click **Connect**.
   - The status label will update to: `Connected. Click New Game to start.`
4. Click **New Game** to start playing.
   - Click any square on the 3x3 board to make a move.
   - The authoritative server handles turns, validates all moves, checks win/draw conditions, and returns the updated board state.

#### Hardware Controls & Indicators
- **SW0 (PA0 Pushbutton):** Pressing SW0 immediately resets the server to `IDLE` state from any state.
- **Red LED (PB10):** Lights up when it is Player X's turn; stays lit continuously if Player X wins.
- **Green LED (PB11):** Lights up when it is Player O's turn; stays lit continuously if Player O wins.
- **Both LEDs (PB10 & PB11):** Flash synchronously at 5 Hz when the game ends in a `DRAW`.

---

### Option B: Software Simulation (No Physical Board Needed)

You can run and test the complete client-server game system on any computer without physical hardware by using the included TCP mock server:

1. **Terminal 1 — Start the Mock Server:**
   ```bash
   python client/mock_stm32.py
   ```
   *(Listens locally on `127.0.0.1:8765` and fully simulates the firmware FSM, framing, and Tic-Tac-Toe rules).*

2. **Terminal 2 — Start the GUI Client:**
   ```bash
   python client/gui.py
   ```
3. Leave the Connection box as **`mock`** and click **Connect**.
4. Click **New Game** and play!

---

## Automated Verification & Testing

### 1. Automated Test Suite (Pytest)
Run the full automated test suite (48 test cases covering protocol framing, server state transitions, invalid inputs, edge cases, and GUI response resilience):
```bash
python -m pytest tests/ -v
```
*All 48 tests execute and pass in under 1 second.*

### 2. Hardware Regression Script
When the physical STM32 board is connected, you can run the automated 26-point hardware assertion script to verify the live MCU firmware:
```bash
python client/test_day3_stm32.py [COM_PORT]
```
*(If omitted, the script automatically searches for and detects the ST-Link Virtual COM Port).*

---

## Communication Protocol Summary

- **Baud Rate:** 115200 bps, 8 data bits, no parity, 1 stop bit (8N1).
- **Framing:** Plain ASCII strings terminated by `\n` (CR `\r` is silently stripped). Maximum frame size is 64 bytes.

| Command | Direction | Expected Server Response | Description |
| :--- | :---: | :--- | :--- |
| `CONNECT` | Client $\to$ Server | `OK\n` | Resets session and synchronizes connection. |
| `NEW` | Client $\to$ Server | `OK:BOARD:.........\n` | Starts a new match from IDLE / GAME_OVER. |
| `MOVE:<X\|O>:<0-8>` | Client $\to$ Server | `OK:BOARD:<grid>\n` / `WIN:<X\|O>\n` / `DRAW\n` | Submits a move on board cell 0–8. |
| `STATE` | Client $\to$ Server | `BOARD:<grid>\n` | Queries current board layout. |
| `RESIGN` | Client $\to$ Server | `OK:GAMEOVER\n` | Current player concedes the active game. |
| `DISCONNECT` | Client $\to$ Server | `OK\n` | Closes active session and returns MCU to IDLE. |
| *Hardware SW0* | Button $\to$ MCU | *Internal reset* | Transitions MCU FSM immediately to IDLE. |

### Error Codes
- `NACK:BADCMD` — Unknown command syntax, frame length $>64$ bytes, or framing timeout ($>500$ ms).
- `NACK:NOGAME` — Move or resign received when no game is active.
- `NACK:NOTURN` — Move attempted by the player whose turn it is not.
- `NACK:OCCUPIED` — Move targeted at an already occupied cell.
- `NACK:RANGE` — Move cell index not between 0 and 8.
