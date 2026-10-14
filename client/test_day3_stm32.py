"""Hardware validation script for Day 3 Tic-Tac-Toe Game Server."""

import sys
import time
import serial
import serial.tools.list_ports

def find_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "STLink" in p.description or "STM" in p.description:
            return p.device
    for p in ports:
        if p.device == "COM9":
            return "COM9"
    return ports[0].device if ports else "COM9"

def send_and_expect(ser, cmd, expected):
    ser.write((cmd + "\n").encode("ascii"))
    line = ser.readline().decode("ascii", errors="replace").strip()
    passed = (line == expected)
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] Sent: {cmd:<16} -> Recv: {line:<20} (Expected: {expected})")
    return passed

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    baud = 115200
    print(f"=== Running Full Day 3 Game Server Test on {port} @ {baud} ===\n")

    try:
        ser = serial.Serial(port, baud, timeout=1.0)
    except Exception as e:
        print(f"[ERROR] Could not open {port}: {e}")
        print("Please ensure your STM32 board is plugged into USB.")
        return

    time.sleep(0.1)
    ser.reset_input_buffer()

    tests = [
        # 1. Connection & Session Reset
        ("CONNECT", "OK"),
        ("STATE", "BOARD:........."),

        # 2. Start Game
        ("NEW", "OK:BOARD:........."),

        # 3. Legal move & board update
        ("MOVE:X:0", "OK:BOARD:X........"),
        ("STATE", "BOARD:X........"),

        # 4. Out-of-turn rejection (X tries to move twice)
        ("MOVE:X:1", "NACK:NOTURN"),
        ("STATE", "BOARD:X........"),

        # 5. Occupied cell rejection
        ("MOVE:O:0", "NACK:OCCUPIED"),
        ("STATE", "BOARD:X........"),

        # 6. Out of range rejection
        ("MOVE:O:9", "NACK:RANGE"),
        ("MOVE:O:-1", "NACK:RANGE"),

        # 7. Scripted Win for X:
        ("MOVE:O:3", "OK:BOARD:X..O....."),
        ("MOVE:X:1", "OK:BOARD:XX.O....."),
        ("MOVE:O:4", "OK:BOARD:XX.OO...."),
        ("MOVE:X:2", "WIN:X"),

        # 8. Moves after Game Over rejected
        ("MOVE:O:5", "NACK:NOGAME"),
        ("STATE", "BOARD:XXXOO...."),

        # 9. Resign test
        ("NEW", "OK:BOARD:........."),
        ("MOVE:X:4", "OK:BOARD:....X...."),
        ("RESIGN", "OK:GAMEOVER"),
        ("MOVE:O:0", "NACK:NOGAME"),

        # 10. Scripted Draw test
        ("NEW", "OK:BOARD:........."),
        ("MOVE:X:0", "OK:BOARD:X........"),
        ("MOVE:O:1", "OK:BOARD:XO......."),
        ("MOVE:X:2", "OK:BOARD:XOX......"),
        ("MOVE:O:4", "OK:BOARD:XOX.O...."),
        ("MOVE:X:3", "OK:BOARD:XOXXO...."),
        ("MOVE:O:5", "OK:BOARD:XOXXOO..."),
        ("MOVE:X:7", "OK:BOARD:XOXXOO.X."),
        ("MOVE:O:6", "OK:BOARD:XOXXOOOX."),
        ("MOVE:X:8", "DRAW"),
        ("STATE", "BOARD:XOXXOOOXX"),
        ("MOVE:O:0", "NACK:NOGAME"),

        # 11. Clean Disconnect
        ("DISCONNECT", "OK"),
    ]

    all_passed = True
    for cmd, expected in tests:
        if not send_and_expect(ser, cmd, expected):
            all_passed = False

    ser.close()
    print("\n" + "=" * 60)
    if all_passed:
        print(">>> ALL 26 GAME PROTOCOL TESTS PASSED ON REAL STM32 HARDWARE! <<<")
    else:
        print(">>> Some tests failed. Please check the firmware on the board. <<<")

if __name__ == "__main__":
    main()
