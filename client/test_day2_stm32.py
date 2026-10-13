"""Interactive test script for Day 2 STM32 protocol implementation."""

import sys
import time
import serial
import serial.tools.list_ports

def find_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        if "STLink" in p.description or "STM" in p.description:
            return p.device
    return "COM9"

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    baud = 115200
    print(f"=== Testing STM32 Day 2 Protocol on {port} @ {baud} ===")

    try:
        ser = serial.Serial(port, baud, timeout=1.0)
    except Exception as e:
        print(f"[Error opening {port}]: {e}")
        return

    # Flush initial boot message
    time.sleep(0.1)
    ser.reset_input_buffer()

    commands = [
        ("CONNECT", "OK"),
        ("STATE", "BOARD:........."),
        ("INVALID_CMD", "NACK:BADCMD"),
        ("A" * 70, "NACK:BADCMD"),  # 70 bytes -> exceeds 64 byte limit!
        ("DISCONNECT", "OK"),
    ]

    all_passed = True
    for cmd, expected in commands:
        wire_cmd = (cmd + "\n").encode("ascii")
        ser.write(wire_cmd)
        response = ser.readline().decode("ascii", errors="replace").strip()

        passed = (response == expected)
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] Sent: {cmd[:20]:<20} -> Received: {response:<20} (Expected: {expected})")
        if not passed:
            all_passed = False

    ser.close()
    print("=" * 60)
    if all_passed:
        print("ALL DAY 2 PROTOCOL TESTS PASSED ON REAL STM32 HARDWARE!")
    else:
        print("Some tests failed. Make sure the latest code is flashed to the board.")

if __name__ == "__main__":
    main()
