"""Graphical Tic-Tac-Toe client for the STM32 game server."""

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path when executed directly as a script
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import messagebox

try:
    from client import serial_client
except ImportError:
    import serial_client


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
        self.resign_in_progress = False

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

        self.disconnect_button = tk.Button(
            connection_frame,
            text="Disconnect",
            command=self.disconnect_server,
            state=tk.DISABLED,
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

        # Status message.
        self.status_label = tk.Label(
            root,
            text="Connect to start.",
            font=("Arial", 12),
            pady=5,
        )
        self.status_label.pack()

        self.turn_label = tk.Label(
            root,
            text="Turn: -",
            font=("Arial", 12),
            pady=2,
        )
        self.turn_label.pack()

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

        self.resign_button = tk.Button(
            control_frame,
            text="Resign",
            command=self.resign_game,
            state=tk.DISABLED,
        )
        self.resign_button.pack(side=tk.LEFT, padx=5)

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

        response = serial_client.send_command("STATE")

        if response is None:
            self.communication_error(
                "Could not synchronize with the server. "
                "The displayed board may be stale; reconnect."
            )
            return

        if not response.startswith("BOARD:") or not self.read_board(
            response[len("BOARD:"):]
        ):
            self.communication_error(
                "The server returned an invalid board. "
                "The displayed board may be stale; reconnect."
            )
            return

        self.current_player = "X"
        self.game_started = False
        self.connected = True
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.DISABLED)
        self.new_game_button.config(state=tk.NORMAL)
        self.state_button.config(state=tk.NORMAL)

        self.update_board()
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
        self.status_label.config(text="New game started.")

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

            previous_board = self.board.copy()
            if len(board_text) != 9 or any(
                cell not in ".XO" for cell in board_text
            ):
                self.game_started = False
                self.update_board()
                error_message = (
                    "The server returned an invalid board. "
                    "Moves are disabled until the board is safely "
                    "resynchronized."
                )
                self.status_label.config(
                    text=error_message
                )
                messagebox.showerror(
                    "Invalid Server Board",
                    error_message,
                )
                return

            response_board = list(board_text)
            if response_board[index] != self.current_player or any(
                response_board[cell] != previous_board[cell]
                for cell in range(9)
                if cell != index
            ):
                self.game_started = False
                self.update_board()
                error_message = (
                    "The server returned a board inconsistent with the "
                    "move. Moves are disabled until the board is safely "
                    "resynchronized."
                )
                self.status_label.config(text=error_message)
                messagebox.showerror(
                    "Board Synchronization Error",
                    error_message,
                )
                return

            self.board = response_board
            self.current_player = (
                "O" if self.current_player == "X" else "X"
            )

            self.update_board()
            self.status_label.config(text="Move accepted.")

        elif response.startswith("WIN:"):
            winner = response.split(":", 1)[1]

            if winner not in ("X", "O"):
                self.status_label.config(
                    text=f"Unexpected response: {response}"
                )
                return

            if not self.read_board_after_terminal_move():
                return

            self.game_started = False

            self.update_board()
            self.status_label.config(text=f"{winner} wins!")

            messagebox.showinfo("Game Over", f"Player {winner} wins!")

        elif response == "DRAW":
            if not self.read_board_after_terminal_move():
                return

            self.game_started = False

            self.update_board()
            self.status_label.config(text="It's a draw!")

            messagebox.showinfo("Game Over", "It's a draw!")

        elif response == "NACK:NOGAME":
            self.game_started = False
            self.update_board()
            self.status_label.config(
                text="There is no active game. Start a new game."
            )

        elif response.startswith("NACK:"):
            error_messages = {
                "NACK:OCCUPIED": "That square is already occupied!",
                "NACK:NOTURN": "It's not your turn!",
                "NACK:RANGE": "Invalid square!",
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

    def read_board_after_terminal_move(self):
        """Read the board after a win or draw response."""
        response = serial_client.send_command("STATE")

        if response is None:
            self.communication_error()
            return False

        if not response.startswith("BOARD:") or not self.read_board(
            response[len("BOARD:"):]
        ):
            self.game_started = False
            self.update_board()
            self.status_label.config(
                text="Could not refresh final board. Start a new game."
            )
            messagebox.showerror(
                "Board Refresh Error",
                "The server did not provide a valid final board. "
                "Moves are disabled until you start a new game.",
            )
            return False

        return True

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
                self.game_started = False
                self.update_board()
                self.status_label.config(
                    text=(
                        "The server returned an invalid board. "
                        "Moves are disabled until the board is safely "
                        "resynchronized."
                    )
                )
                return

            self.read_board(board_text)
            self.update_board()
            self.status_label.config(text="Board refreshed.")

        else:
            self.status_label.config(
                text=f"Could not refresh board: {response}"
            )

    def resign_game(self):
        """Ask the server to end the active game by resignation."""
        if (
            not self.connected
            or not self.game_started
            or self.resign_in_progress
        ):
            return

        if not messagebox.askyesno(
            "Resign Game",
            "Are you sure you want to resign?",
        ):
            return

        self.resign_in_progress = True
        self.resign_button.config(state=tk.DISABLED)

        try:
            response = serial_client.send_command("RESIGN")
        except Exception as error:
            self.resign_in_progress = False
            self.communication_error(
                f"Could not confirm resignation: {error}"
            )
            return

        self.resign_in_progress = False

        if response == "OK:GAMEOVER":
            self.game_started = False
            self.update_board()
            self.status_label.config(text="Game ended by resignation.")
            return

        if response is None or response == "":
            self.communication_error(
                "Could not confirm resignation. Reconnect."
            )
            return

        if response == "NACK:NOGAME":
            self.game_started = False

        self.update_board()
        error_message = (
            "The server did not confirm resignation "
            f"(response: {response})."
        )
        self.status_label.config(text=error_message)
        messagebox.showerror("Resignation Error", error_message)

    def update_board(self):
        """Display the board and enable squares during an active game."""
        self.turn_label.config(
            text=(
                f"Turn: {self.current_player}"
                if self.connected and self.game_started
                else "Turn: -"
            )
        )

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

        self.resign_button.config(
            state=(
                tk.NORMAL
                if (
                    self.connected
                    and self.game_started
                    and not self.resign_in_progress
                )
                else tk.DISABLED
            )
        )

    def communication_error(
        self,
        error_message=None,
    ):
        """Handle a missing server response."""
        self.game_started = False
        self.connected = False
        serial_client.disconnect()

        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)
        self.new_game_button.config(state=tk.DISABLED)
        self.state_button.config(state=tk.DISABLED)

        self.update_board()

        status_message = error_message or "Communication failed. Reconnect."
        dialog_message = error_message or (
            "No valid response from the server. "
            "Check the connection and reconnect."
        )
        self.status_label.config(text=status_message)

        messagebox.showerror(
            "Communication Error",
            dialog_message,
        )

    def disconnect_server(self):
        """Disconnect from the server and leave game controls disabled."""
        was_connected = self.connected
        acknowledged = False
        error_message = "The server did not acknowledge DISCONNECT."

        if was_connected:
            try:
                response = serial_client.send_command("DISCONNECT")
                if response == "OK":
                    acknowledged = True
                else:
                    error_message = (
                        "The server did not acknowledge DISCONNECT "
                        f"(response: {response!r})."
                    )
            except Exception as error:
                error_message = (
                    f"Could not confirm DISCONNECT: {error}"
                )

        try:
            serial_client.disconnect()
        except Exception as error:
            acknowledged = False
            error_message = f"Could not close the serial connection: {error}"

        self.connected = False
        self.game_started = False
        self.connect_button.config(state=tk.NORMAL)
        self.disconnect_button.config(state=tk.DISABLED)
        self.port_entry.config(state=tk.NORMAL)
        self.new_game_button.config(state=tk.DISABLED)
        self.state_button.config(state=tk.DISABLED)
        self.update_board()

        if acknowledged:
            self.status_label.config(text="Disconnected.")
            return True

        if was_connected:
            self.status_label.config(
                text=error_message + " The connection was closed locally."
            )
            messagebox.showerror(
                "Disconnect Error",
                error_message + " The connection was closed locally.",
            )
        else:
            self.status_label.config(text="Not connected.")

        return False

    def close_window(self):
        """Close the connection before exiting."""
        try:
            self.disconnect_server()
        finally:
            self.root.destroy()


def main():
    """Start the GUI."""
    root = tk.Tk()
    TicTacToeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
