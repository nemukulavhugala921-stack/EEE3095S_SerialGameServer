
"""Mock STM32 Tic-Tac-Toe server for local development.

This simulates the agreed game protocol over a local TCP connection.
It does not replace or prove the real STM32 firmware works.
"""

import socket
import time

# Local development connection settings.
HOST = "127.0.0.1"
PORT = 8765
MAX_FRAME_LENGTH = 64
PARTIAL_FRAME_TIMEOUT = 1.0

# Server states.
IDLE = "IDLE"
IN_PROGRESS = "IN_PROGRESS"
GAME_OVER = "GAME_OVER"

# All eight possible winning combinations.
WINNING_COMBINATIONS = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]


class MockSTM32:
    """Simulate the STM32 game state and command responses."""

    def __init__(self):
        self.reset_session()

    def reset_session(self):
        """Clear the game and return to IDLE."""
        self.state = IDLE
        self.board = ["."] * 9
        self.current_player = "X"

    def handle_command(self, command):
        """Process one complete command without its line ending."""

        if command == "CONNECT":
            self.reset_session()
            return "OK"

        if command == "DISCONNECT":
            self.reset_session()
            return "OK"

        if command == "NEW":
            if self.state not in (IDLE, GAME_OVER):
                return "NACK:BADCMD"

            self.board = ["."] * 9
            self.current_player = "X"
            self.state = IN_PROGRESS
            return "OK:BOARD:........."

        if command == "STATE":
            return "BOARD:" + "".join(self.board)

        if command == "RESIGN":
            if self.state != IN_PROGRESS:
                return "NACK:NOGAME"

            self.state = GAME_OVER
            return "OK:GAMEOVER"

        if command.startswith("MOVE:"):
            parts = command.split(":")

            # A move must contain a player and a square index.
            if len(parts) != 3:
                return "NACK:BADCMD"

            _, player, index_text = parts

            # Only X and O are valid players.
            if player not in ("X", "O"):
                return "NACK:BADCMD"

            # A move is only allowed during an active game.
            if self.state != IN_PROGRESS:
                return "NACK:NOGAME"

            # The square index must be a decimal number.
            if not index_text.isascii() or not index_text.isdigit():
                return "NACK:RANGE"

            index = int(index_text)

            if not 0 <= index <= 8:
                return "NACK:RANGE"

            # Reject moves from the wrong player.
            # The board and current turn remain unchanged.
            if player != self.current_player:
                return "NACK:NOTURN"

            # Apply the legal move.
            return self.handle_move(index_text)

        return "NACK:BADCMD"

    def handle_move(self, index_text):
        """Validate a move and return the server's response."""

        # Only non-negative decimal digits are accepted.
        if not index_text.isascii() or not index_text.isdigit():
            return "NACK:RANGE"

        index = int(index_text)

        if not 0 <= index <= 8:
            return "NACK:RANGE"

        if self.state != IN_PROGRESS:
            return "NACK:NOGAME"

        if self.board[index] != ".":
            return "NACK:OCCUPIED"

        # Apply the move using the current player.
        self.board[index] = self.current_player

        # Check whether this move wins the game.
        if self.has_won(self.current_player):
            winner = self.current_player
            self.state = GAME_OVER
            return f"WIN:{winner}"

        # Check whether all squares are filled.
        if "." not in self.board:
            self.state = GAME_OVER
            return "DRAW"

        # Switch player after a non-terminal move.
        self.current_player = (
            "O" if self.current_player == "X" else "X"
        )

        return "OK:BOARD:" + "".join(self.board)

    def has_won(self, player):
        """Check all eight winning combinations."""
        return any(
            all(self.board[i] == player for i in combo)
            for combo in WINNING_COMBINATIONS
        )


def serve_client(connection, address):
    """Receive newline-terminated commands and return responses."""

    print(f"Client connected: {address}")

    server = MockSTM32()
    buffer = bytearray()
    discarding_oversized_frame = False
    last_byte_at = None

    try:
        connection.settimeout(PARTIAL_FRAME_TIMEOUT)

        with connection:
            while True:
                try:
                    data = connection.recv(1024)
                except socket.timeout:
                    if last_byte_at is not None:
                        remaining = PARTIAL_FRAME_TIMEOUT - (
                            time.monotonic() - last_byte_at
                        )

                        if remaining <= 0:
                            buffer.clear()
                            discarding_oversized_frame = False
                            last_byte_at = None
                            connection.settimeout(PARTIAL_FRAME_TIMEOUT)
                            connection.sendall(b"NACK:BADCMD\n")
                            print("Response: NACK:BADCMD")
                        else:
                            connection.settimeout(remaining)

                    continue

                if not data:
                    break

                connection.settimeout(PARTIAL_FRAME_TIMEOUT)

                for byte in data:
                    if byte == ord("\n"):
                        last_byte_at = None

                        if discarding_oversized_frame:
                            response = "NACK:BADCMD"
                            discarding_oversized_frame = False
                            buffer.clear()

                        else:
                            # Support both LF and CRLF line endings.
                            if buffer.endswith(b"\r"):
                                buffer.pop()

                            try:
                                command = buffer.decode("ascii")
                                response = server.handle_command(command)
                            except UnicodeDecodeError:
                                response = "NACK:BADCMD"

                            buffer.clear()

                        connection.sendall(
                            (response + "\n").encode("ascii")
                        )
                        print(f"Response: {response}")

                    elif discarding_oversized_frame:
                        # Ignore the rest until the frame's newline.
                        last_byte_at = time.monotonic()
                        continue

                    elif len(buffer) >= MAX_FRAME_LENGTH:
                        # Discard frames that exceed the 64-byte limit.
                        buffer.clear()
                        discarding_oversized_frame = True
                        last_byte_at = time.monotonic()

                    else:
                        buffer.append(byte)
                        last_byte_at = time.monotonic()

    except OSError as error:
        print(f"Connection error: {error}")

    finally:
        print(f"Client disconnected: {address}")


def main():
    """Start the local mock server."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )
        server_socket.bind((HOST, PORT))
        server_socket.listen()

        print("Mock STM32 server is running.")
        print(f"Listening on {HOST}:{PORT}")
        print("Press Ctrl+C to stop.")

        try:
            while True:
                connection, address = server_socket.accept()
                serve_client(connection, address)

        except KeyboardInterrupt:
            print("\nStopping mock STM32 server.")


if __name__ == "__main__":
    main()
