
"""Graphical Tic-Tac-Toe client for the STM32 game server."""

import tkinter as tk
from tkinter import messagebox

from client import serial_client


class TicTacToeGUI:
    """Display the board and communicate with the game server."""

    def __init__(self, root):
        self.root = root
        self.root.title("STM32 Tic-Tac-Toe")
        self.root.resizable(False, False)

        self.board = ["."] * 9
        self.connected = False
        self.game_started = False
        self.current_player = "X"

        # Connection controls.
        connection_frame = tk.Frame(root, padx=10, pady=10)
        connection_frame.pack()

        tk.Label(connection_frame, text="Connection:").pack(side=tk.LEFT)

        self.port_entry = tk.Entry(connection_frame, width=10)
        self.port_entry.insert(0, "mock")
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.connect_button = tk.Button(
            connection_frame,
            text="Connect",
            command=self.connect_server,
        )
        self.connect_button.pack(side=tk.LEFT)

        # Status message.
        self.status_label = tk.Label(
            root,
            text="Connect to start.",
            font=("Arial", 12),
            pady=5,
        )
        self.status_label.pack()

        # Tic-Tac-Toe board.
        board_frame = tk.Frame(root, padx=10, pady=10)
        board_frame.pack()

        self.square_buttons = []

        for index in range(9):
            button = tk.Button(
                board_frame,
                text="",
                font=("Arial", 24, "bold"),
                width=4,
                height=2,
                command=lambda i=index: self.make_move(i),
                state=tk.DISABLED,
            )

            button.grid(
                row=index // 3,
                column=index % 3,
                padx=3,
                pady=3,
            )

            self.square_buttons.append(button)

        # Game controls.
        control_frame = tk.Frame(root, padx=10, pady=10)
        control_frame.pack()

        self.new_game_button = tk.Button(
            control_frame,
            text="New Game",
            command=self.new_game,
            state=tk.DISABLED,
        )
        self.new_game_button.pack(side=tk.LEFT, padx=5)

        self.state_button = tk.Button(
            control_frame,
            text="Refresh Board",
            command=self.refresh_board,
            state=tk.DISABLED,
        )
        self.state_button.pack(side=tk.LEFT, padx=5)

        self.root.protocol("WM_DELETE_WINDOW", self.close_window)

    def connect_server(self):
        """Connect to the mock server or a serial port."""
        port = self.port_entry.get().strip()

        if not port:
            messagebox.showerror(
                "Connection Error",
                "Enter a port or 'mock'.",
            )
            return

        if not serial_client.connect(port):
            messagebox.showerror(
                "Connection Error",
                f"Could not connect using '{port}'.\n"
                "For local testing, start the mock server first.",
            )
            return

        response = serial_client.send_command("CONNECT")

        if response != "OK":
            serial_client.disconnect()
            messagebox.showerror(
                "Connection Error",
                "The server did not respond correctly to CONNECT.",
            )
            return

        self.connected = True
        self.connect_button.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.DISABLED)
        self.new_game_button.config(state=tk.NORMAL)
        self.state_button.config(state=tk.NORMAL)

        self.status_label.config(text="Connected. Select New Game.")

    def new_game(self):
        """Ask the server to start a new game."""
        if not self.connected:
            return

        response = serial_client.send_command("NEW")

        if response is None:
            self.communication_error()
            return

        if response != "OK:BOARD:.........":
            self.status_label.config(
                text=f"Could not start game: {response}"
            )
            return

        self.board = ["."] * 9
        self.current_player = "X"
        self.game_started = True

        self.update_board()
        self.status_label.config(text="X's turn.")

    def make_move(self, index):
        """Send a move and handle the server's response."""
        if not self.connected or not self.game_started:
            return

        # Let the user click occupied squares to show a clear message.
        # Do not send an illegal move to the server.
        if self.board[index] != ".":
            self.status_label.config(
                text="That square is already occupied!"
            )
            return

        command = f"MOVE:{self.current_player}:{index}"
        response = serial_client.send_command(command)

        if response is None:
            self.communication_error()
            return

        if response.startswith("OK:BOARD:"):
            board_text = response[len("OK:BOARD:"):]

            if not self.read_board(board_text):
                self.status_label.config(
                    text="Invalid board from server."
                )
                return

            self.current_player = (
                "O" if self.current_player == "X" else "X"
            )

            self.update_board()
            self.status_label.config(
                text=f"{self.current_player}'s turn."
            )

        elif response.startswith("WIN:"):
            winner = response.split(":", 1)[1]

            if winner not in ("X", "O"):
                self.status_label.config(
                    text=f"Unexpected response: {response}"
                )
                return

            self.read_board_after_terminal_move(index)
            self.game_started = False

            self.update_board()
            self.status_label.config(text=f"{winner} wins!")

            messagebox.showinfo("Game Over", f"Player {winner} wins!")

        elif response == "DRAW":
            self.read_board_after_terminal_move(index)
            self.game_started = False

            self.update_board()
            self.status_label.config(text="It's a draw!")

            messagebox.showinfo("Game Over", "It's a draw!")

        elif response.startswith("NACK:"):
            error_messages = {
                "NACK:OCCUPIED": "That square is already occupied!",
                "NACK:NOTURN": "It's not your turn!",
                "NACK:RANGE": "Invalid square!",
                "NACK:NOGAME": "There is no active game. Start a new game.",
                "NACK:BADCMD": "Invalid command.",
            }

            message = error_messages.get(
                response,
                f"Move rejected: {response}",
            )

            self.status_label.config(text=message)

        else:
            self.status_label.config(
                text=f"Unexpected response: {response}"
            )

    def read_board(self, board_text):
        """Update the local board from a server board response."""
        if len(board_text) == 9 and all(
            cell in ".XO" for cell in board_text
        ):
            self.board = list(board_text)
            return True

        return False

    def read_board_after_terminal_move(self, index):
        """Read the board after a win or draw response."""
        response = serial_client.send_command("STATE")

        if response is not None and response.startswith("BOARD:"):
            self.read_board(response[len("BOARD:"):])
        else:
            # Keep the displayed board useful if STATE fails.
            self.board[index] = self.current_player

    def refresh_board(self):
        """Request and display the latest board from the server."""
        if not self.connected:
            self.status_label.config(text="Not connected.")
            return

        response = serial_client.send_command("STATE")

        if response is None:
            self.communication_error()
            return

        if response.startswith("BOARD:"):
            board_text = response[len("BOARD:"):]

            if len(board_text) != 9 or any(
                cell not in ".XO" for cell in board_text
            ):
                self.status_label.config(text="Invalid board from server.")
                return

            self.read_board(board_text)
            self.update_board()
            self.status_label.config(text="Board refreshed.")

        else:
            self.status_label.config(
                text=f"Could not refresh board: {response}"
            )

    def update_board(self):
        """Display the board and enable squares during an active game."""
        for index, button in enumerate(self.square_buttons):
            value = self.board[index]

            button.config(
                text="" if value == "." else value,
                state=(
                    tk.NORMAL
                    if self.connected and self.game_started
                    else tk.DISABLED
                ),
            )

    def communication_error(self):
        """Handle a missing server response."""
        self.game_started = False
        self.connected = False
        serial_client.disconnect()

        self.connect_button.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.new_game_button.config(state=tk.DISABLED)
        self.state_button.config(state=tk.DISABLED)

        self.update_board()

        self.status_label.config(text="Communication failed. Reconnect.")

        messagebox.showerror(
            "Communication Error",
            "No valid response from the server. "
            "Check the connection and reconnect.",
        )

    def close_window(self):
        """Close the connection before exiting."""
        if self.connected:
            serial_client.send_command("DISCONNECT")

        serial_client.disconnect()
        self.root.destroy()


def main():
    """Start the GUI."""
    root = tk.Tk()
    TicTacToeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
