
"""Client communication wrapper for the Tic-Tac-Toe server.

Supports:
- Local TCP mock server for development.
- STM32 board through a serial COM port.
"""

import socket
import serial


# Local mock server settings.
MOCK_HOST = "127.0.0.1"
MOCK_PORT = 8765

# Serial and communication settings.
BAUD_RATE = 115200
TIMEOUT = 1.0
MAX_RESPONSE_LENGTH = 64
SERIAL_STARTUP_BANNER = "STM32 SERIAL SERVER READY"

# Active connection and response reader.
connection = None
reader = None
transport = None


def connect(port="mock"):
    """Connect to the mock server or the STM32 serial port.

    Use connect() or connect("mock") for the local mock server.
    Use connect("COM3") for an STM32 connected on COM3.
    Returns True if successful, otherwise False.
    """
    global connection, reader, transport

    disconnect()

    try:
        if port == "mock":
            connection = socket.create_connection(
                (MOCK_HOST, MOCK_PORT),
                timeout=TIMEOUT,
            )
            connection.settimeout(TIMEOUT)
            reader = connection.makefile("rb")
            transport = "mock"

        else:
            connection = serial.Serial(
                port=port,
                baudrate=BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=TIMEOUT,
                write_timeout=TIMEOUT,
            )
            reader = None
            transport = "serial"

        return True

    except (OSError, serial.SerialException, ValueError):
        disconnect()
        return False


def send_command(command):
    """Send one command and return one response without its newline.

    Returns None if disconnected or a communication error occurs.
    """
    global connection

    if connection is None or transport is None:
        return None

    try:
        # Send an ASCII command followed by a newline.
        message = (command.strip() + "\n").encode("ascii")
        connection.sendall(message) if transport == "mock" else connection.write(message)

        # Read the response one byte at a time.
        while True:
            response = bytearray()

            while len(response) < MAX_RESPONSE_LENGTH:
                if transport == "mock":
                    byte = reader.read(1)
                else:
                    byte = connection.read(1)

                if not byte:
                    disconnect()
                    return None

                if byte == b"\n":
                    break

                if byte != b"\r":
                    response.extend(byte)
            else:
                disconnect()
                return None

            response_text = response.decode("ascii")

            if (
                transport == "serial"
                and response_text == SERIAL_STARTUP_BANNER
            ):
                continue

            return response_text

    except (OSError, serial.SerialException, UnicodeDecodeError):
        disconnect()
        return None
    except ValueError:
        return None


def disconnect():
    """Close the current connection safely."""
    global connection, reader, transport

    if reader is not None:
        try:
            reader.close()
        except OSError:
            pass

    if connection is not None:
        try:
            connection.close()
        except (OSError, serial.SerialException):
            pass

    connection = None
    reader = None
    transport = None


if __name__ == "__main__":
    # Simple manual test using the local mock server.
    if connect():
        print("Connected to mock server.")

        for command in ("CONNECT", "NEW", "MOVE:X:0", "STATE"):
            print(f"{command} -> {send_command(command)}")

        disconnect()
        print("Disconnected.")
    else:
        print("Could not connect. Is the mock server running?")
