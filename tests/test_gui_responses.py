"""Response-validation tests for the graphical client."""

import pytest

from client import gui


class StatusLabel:
    def __init__(self):
        self.options = {}

    def config(self, **options):
        self.options.update(options)


class Widget:
    def __init__(self):
        self.options = {}

    def config(self, **options):
        self.options.update(options)


class PortEntry(Widget):
    def get(self):
        return "COM_TEST"


@pytest.fixture
def active_gui():
    instance = gui.TicTacToeGUI.__new__(gui.TicTacToeGUI)
    instance.connected = True
    instance.game_started = True
    instance.board = ["."] * 9
    instance.current_player = "X"
    instance.status_label = StatusLabel()
    instance.turn_label = StatusLabel()
    instance.connect_button = Widget()
    instance.disconnect_button = Widget()
    instance.port_entry = PortEntry()
    instance.new_game_button = Widget()
    instance.state_button = Widget()
    instance.resign_button = Widget()
    instance.resign_in_progress = False
    instance.update_board = lambda: None
    return instance


def make_connectable_gui(board):
    instance = gui.TicTacToeGUI.__new__(gui.TicTacToeGUI)
    instance.connected = False
    instance.game_started = False
    instance.current_player = "O"
    instance.board = list(board)
    instance.status_label = StatusLabel()
    instance.turn_label = StatusLabel()
    instance.port_entry = PortEntry()
    instance.connect_button = Widget()
    instance.disconnect_button = Widget()
    instance.new_game_button = Widget()
    instance.state_button = Widget()
    instance.resign_button = Widget()
    instance.resign_in_progress = False
    instance.square_buttons = [Widget() for _ in range(9)]
    instance.update_board = lambda: gui.TicTacToeGUI.update_board(instance)
    return instance


def test_reconnect_synchronizes_existing_board_before_enabling_game(
    monkeypatch,
):
    instance = make_connectable_gui("X.O......")
    commands = []
    monkeypatch.setattr(gui.serial_client, "connect", lambda port: True)

    def send_command(command):
        commands.append(command)
        return {
            "CONNECT": "OK",
            "STATE": "BOARD:.........",
        }[command]

    monkeypatch.setattr(gui.serial_client, "send_command", send_command)

    instance.connect_server()

    assert commands == ["CONNECT", "STATE"]
    assert instance.board == ["."] * 9
    assert instance.current_player == "X"
    assert instance.game_started is False
    assert instance.connected is True
    assert instance.disconnect_button.options["state"] == gui.tk.NORMAL
    assert instance.new_game_button.options["state"] == gui.tk.NORMAL
    assert instance.state_button.options["state"] == gui.tk.NORMAL
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in instance.square_buttons
    )
    assert (
        instance.status_label.options["text"]
        == "Connected. Select New Game."
    )
    assert instance.turn_label.options["text"] == "Turn: -"


def test_turn_display_stays_separate_from_move_and_refresh_feedback(
    active_gui,
    monkeypatch,
):
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    responses = iter(("OK:BOARD:X........", "BOARD:X........"))
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: next(responses),
    )

    active_gui.make_move(0)

    assert active_gui.turn_label.options["text"] == "Turn: O"
    assert active_gui.status_label.options["text"] == "Move accepted."

    active_gui.refresh_board()

    assert active_gui.turn_label.options["text"] == "Turn: O"
    assert active_gui.status_label.options["text"] == "Board refreshed."

    active_gui.make_move(0)

    assert active_gui.turn_label.options["text"] == "Turn: O"
    assert (
        active_gui.status_label.options["text"]
        == "That square is already occupied!"
    )


@pytest.mark.parametrize(
    ("state_response", "expected_status"),
    [
        (
            None,
            "Could not synchronize with the server. "
            "The displayed board may be stale; reconnect.",
        ),
        (
            "BOARD:bad",
            "The server returned an invalid board. "
            "The displayed board may be stale; reconnect.",
        ),
    ],
)
def test_connect_does_not_accept_failed_or_invalid_state(
    monkeypatch,
    state_response,
    expected_status,
):
    previous_board = "X.O......"
    instance = make_connectable_gui(previous_board)
    commands = []
    disconnected = []
    errors = []
    monkeypatch.setattr(gui.serial_client, "connect", lambda port: True)

    def send_command(command):
        commands.append(command)
        return "OK" if command == "CONNECT" else state_response

    monkeypatch.setattr(gui.serial_client, "send_command", send_command)
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )

    instance.connect_server()

    assert commands == ["CONNECT", "STATE"]
    assert instance.board == list(previous_board)
    assert instance.current_player == "O"
    assert instance.game_started is False
    assert instance.connected is False
    assert instance.connect_button.options["state"] == gui.tk.NORMAL
    assert instance.new_game_button.options["state"] == gui.tk.DISABLED
    assert instance.state_button.options["state"] == gui.tk.DISABLED
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in instance.square_buttons
    )
    assert instance.status_label.options["text"] == expected_status
    assert disconnected == [True]
    assert errors[0][0] == "Communication Error"


@pytest.mark.parametrize(
    ("response", "expected_status"),
    [
        ("NACK:NOTURN", "It's not your turn!"),
        (
            "OK:BOARD:invalid",
            "The server returned an invalid board. "
            "Moves are disabled until the board is safely "
            "resynchronized.",
        ),
        ("WIN:Q", "Unexpected response: WIN:Q"),
    ],
)
def test_rejected_or_malformed_responses_do_not_change_local_game(
    active_gui,
    monkeypatch,
    response,
    expected_status,
):
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: response,
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: None,
    )

    active_gui.make_move(4)

    assert active_gui.board == ["."] * 9
    assert active_gui.current_player == "X"
    assert active_gui.game_started is (response != "OK:BOARD:invalid")
    assert active_gui.status_label.options["text"] == expected_status


def test_malformed_move_board_keeps_confirmed_board_and_disables_moves(
    active_gui,
    monkeypatch,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.new_game_button = Widget()
    active_gui.state_button = Widget()
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    errors = []
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: "OK:BOARD:invalid",
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )

    active_gui.make_move(2)

    assert active_gui.board == confirmed_board
    assert active_gui.game_started is False
    assert active_gui.connected is True
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in active_gui.square_buttons
    )
    assert active_gui.status_label.options["text"] == (
        "The server returned an invalid board. "
        "Moves are disabled until the board is safely resynchronized."
    )
    assert errors[0][0] == "Invalid Server Board"


@pytest.mark.parametrize(
    "response_board",
    [
        "XO.......",
        "XOXO.....",
    ],
)
def test_inconsistent_move_board_preserves_confirmed_board_and_disables_moves(
    active_gui,
    monkeypatch,
    response_board,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.new_game_button = Widget()
    active_gui.state_button = Widget()
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    errors = []
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: f"OK:BOARD:{response_board}",
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )

    active_gui.make_move(2)

    assert active_gui.board == confirmed_board
    assert active_gui.game_started is False
    assert active_gui.connected is True
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in active_gui.square_buttons
    )
    assert active_gui.status_label.options["text"] == (
        "The server returned a board inconsistent with the move. "
        "Moves are disabled until the board is safely resynchronized."
    )
    assert errors[0][0] == "Board Synchronization Error"


def test_no_active_game_stops_moves_without_changing_confirmed_board(
    active_gui,
    monkeypatch,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: "NACK:NOGAME",
    )

    active_gui.make_move(2)

    assert active_gui.board == confirmed_board
    assert active_gui.game_started is False
    assert active_gui.connected is True
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in active_gui.square_buttons
    )
    assert active_gui.status_label.options["text"] == (
        "There is no active game. Start a new game."
    )


def test_invalid_refresh_board_preserves_board_and_disables_moves(
    active_gui,
    monkeypatch,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: "BOARD:invalid",
    )

    active_gui.refresh_board()

    assert active_gui.board == confirmed_board
    assert active_gui.game_started is False
    assert active_gui.connected is True
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in active_gui.square_buttons
    )
    assert active_gui.status_label.options["text"] == (
        "The server returned an invalid board. "
        "Moves are disabled until the board is safely resynchronized."
    )


def test_resign_button_tracks_connection_and_game_state(active_gui):
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )

    assert active_gui.resign_button is not None
    active_gui.update_board()
    assert active_gui.resign_button.options["state"] == gui.tk.NORMAL

    active_gui.game_started = False
    active_gui.update_board()
    assert active_gui.resign_button.options["state"] == gui.tk.DISABLED

    active_gui.game_started = True
    active_gui.connected = False
    active_gui.update_board()
    assert active_gui.resign_button.options["state"] == gui.tk.DISABLED


def test_gui_creates_disabled_resign_button(monkeypatch):
    widgets = []

    class FakeWidget:
        def __init__(self, *args, **options):
            self.options = options
            widgets.append(self)

        def pack(self, *args, **kwargs):
            pass

        def grid(self, *args, **kwargs):
            pass

        def insert(self, *args, **kwargs):
            pass

        def title(self, *args, **kwargs):
            pass

        def resizable(self, *args, **kwargs):
            pass

        def protocol(self, *args, **kwargs):
            pass

    monkeypatch.setattr(gui.tk, "Frame", FakeWidget)
    monkeypatch.setattr(gui.tk, "Label", FakeWidget)
    monkeypatch.setattr(gui.tk, "Entry", FakeWidget)
    monkeypatch.setattr(gui.tk, "Button", FakeWidget)

    instance = gui.TicTacToeGUI(FakeWidget())

    resign_buttons = [
        widget for widget in widgets
        if widget.options.get("text") == "Resign"
    ]
    assert len(resign_buttons) == 1
    assert resign_buttons[0].options["state"] == gui.tk.DISABLED
    assert resign_buttons[0].options["command"] == instance.resign_game


def test_cancel_resignation_sends_no_command_or_changes_game(
    active_gui,
    monkeypatch,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    commands = []
    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: False,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: commands.append(command),
    )

    active_gui.resign_game()

    assert commands == []
    assert active_gui.connected is True
    assert active_gui.game_started is True
    assert active_gui.board == confirmed_board
    assert active_gui.resign_button.options == {}


def test_confirmed_resignation_preserves_board_and_disables_moves(
    active_gui,
    monkeypatch,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    commands = []
    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: True,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: commands.append(command) or "OK:GAMEOVER",
    )

    active_gui.resign_game()

    assert commands == ["RESIGN"]
    assert active_gui.connected is True
    assert active_gui.game_started is False
    assert active_gui.board == confirmed_board
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in active_gui.square_buttons
    )
    assert active_gui.resign_button.options["state"] == gui.tk.DISABLED
    assert active_gui.status_label.options["text"] == (
        "Game ended by resignation."
    )
    assert active_gui.resign_in_progress is False


@pytest.mark.parametrize("response", ["NACK:BADCMD", "unexpected response"])
def test_resignation_rejection_does_not_report_success(
    active_gui,
    monkeypatch,
    response,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    errors = []
    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: True,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: response,
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )

    active_gui.resign_game()

    assert active_gui.connected is True
    assert active_gui.game_started is True
    assert active_gui.board == confirmed_board
    assert active_gui.resign_button.options["state"] == gui.tk.NORMAL
    assert active_gui.status_label.options["text"] == (
        "The server did not confirm resignation "
        f"(response: {response})."
    )
    assert errors[0][0] == "Resignation Error"


def test_nogame_resignation_rejection_stops_local_game(
    active_gui,
    monkeypatch,
):
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: True,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: "NACK:NOGAME",
    )
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: None)

    active_gui.resign_game()

    assert active_gui.connected is True
    assert active_gui.game_started is False
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in active_gui.square_buttons
    )
    assert active_gui.resign_button.options["state"] == gui.tk.DISABLED
    assert active_gui.status_label.options["text"] != (
        "Game ended by resignation."
    )


@pytest.mark.parametrize("response", [None, ""])
def test_missing_resignation_response_uses_communication_error(
    active_gui,
    monkeypatch,
    response,
):
    disconnected = []
    errors = []
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: True,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: response,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )

    active_gui.resign_game()

    assert active_gui.connected is False
    assert active_gui.game_started is False
    assert active_gui.resign_button.options["state"] == gui.tk.DISABLED
    assert disconnected == [True]
    assert errors[0][0] == "Communication Error"
    assert "Game ended by resignation" not in (
        active_gui.status_label.options["text"]
    )


def test_resignation_communication_exception_is_safe(
    active_gui,
    monkeypatch,
):
    disconnected = []
    errors = []
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )

    def raise_error(command):
        raise OSError("serial write failed")

    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: True,
    )
    monkeypatch.setattr(gui.serial_client, "send_command", raise_error)
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )

    active_gui.resign_game()

    assert active_gui.connected is False
    assert active_gui.game_started is False
    assert active_gui.resign_button.options["state"] == gui.tk.DISABLED
    assert disconnected == [True]
    assert errors[0][0] == "Communication Error"
    assert active_gui.resign_in_progress is False


@pytest.mark.parametrize(
    ("connected", "game_started"),
    [(False, True), (True, False)],
)
def test_resignation_is_ignored_when_not_available(
    active_gui,
    monkeypatch,
    connected,
    game_started,
):
    commands = []
    confirmations = []
    active_gui.connected = connected
    active_gui.game_started = game_started
    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: confirmations.append(args) or True,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: commands.append(command),
    )

    active_gui.resign_game()

    assert confirmations == []
    assert commands == []


def test_resignation_request_cannot_be_sent_twice(
    active_gui,
    monkeypatch,
):
    commands = []
    monkeypatch.setattr(
        gui.messagebox,
        "askyesno",
        lambda *args: True,
    )

    def send_command(command):
        commands.append(command)
        active_gui.resign_game()
        return "OK:GAMEOVER"

    monkeypatch.setattr(gui.serial_client, "send_command", send_command)

    active_gui.resign_game()

    assert commands == ["RESIGN"]
    assert active_gui.game_started is False


def test_communication_error_allows_reconnection(active_gui, monkeypatch):
    active_gui.connect_button = Widget()
    active_gui.disconnect_button = Widget()
    active_gui.port_entry = Widget()
    active_gui.new_game_button = Widget()
    active_gui.state_button = Widget()
    disconnected = []
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: None)

    active_gui.communication_error()

    assert active_gui.connected is False
    assert active_gui.game_started is False
    assert active_gui.connect_button.options["state"] == gui.tk.NORMAL
    assert active_gui.disconnect_button.options["state"] == gui.tk.DISABLED
    assert active_gui.port_entry.options["state"] == gui.tk.NORMAL
    assert active_gui.new_game_button.options["state"] == gui.tk.DISABLED
    assert active_gui.state_button.options["state"] == gui.tk.DISABLED
    assert disconnected == [True]


@pytest.mark.parametrize(
    ("state_response", "expected_status"),
    [
        (None, "Communication failed. Reconnect."),
        (
            "BOARD:invalid",
            "Could not refresh final board. Start a new game.",
        ),
    ],
)
def test_terminal_move_keeps_last_confirmed_board_when_state_refresh_fails(
    active_gui,
    monkeypatch,
    state_response,
    expected_status,
):
    confirmed_board = list("XO.......")
    active_gui.board = confirmed_board.copy()
    active_gui.square_buttons = [Widget() for _ in range(9)]
    active_gui.update_board = lambda: gui.TicTacToeGUI.update_board(
        active_gui
    )
    active_gui.connect_button = Widget()
    active_gui.port_entry = Widget()
    active_gui.new_game_button = Widget()
    active_gui.state_button = Widget()
    responses = iter(("WIN:X", state_response))
    errors = []
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: next(responses),
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )
    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *args: None)

    active_gui.make_move(2)

    assert active_gui.board == confirmed_board
    assert active_gui.game_started is False
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in active_gui.square_buttons
    )
    assert active_gui.status_label.options["text"] == expected_status

    if state_response is None:
        assert active_gui.connected is False
    else:
        assert active_gui.connected is True
        assert errors[0][0] == "Board Refresh Error"

    active_gui.make_move(3)
    assert active_gui.board == confirmed_board


def make_disconnectable_gui():
    instance = gui.TicTacToeGUI.__new__(gui.TicTacToeGUI)
    instance.connected = True
    instance.game_started = True
    instance.current_player = "X"
    instance.board = list("XO.......")
    instance.status_label = StatusLabel()
    instance.turn_label = StatusLabel()
    instance.connect_button = Widget()
    instance.disconnect_button = Widget()
    instance.port_entry = Widget()
    instance.new_game_button = Widget()
    instance.state_button = Widget()
    instance.resign_button = Widget()
    instance.resign_in_progress = False
    instance.square_buttons = [Widget() for _ in range(9)]
    instance.update_board = lambda: gui.TicTacToeGUI.update_board(instance)
    return instance


class Root:
    destroyed = False

    def destroy(self):
        self.destroyed = True


def test_disconnect_button_sends_command_and_keeps_window_open(
    monkeypatch,
):
    instance = make_disconnectable_gui()
    instance.root = Root()
    commands = []
    disconnected = []
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: commands.append(command) or "OK",
    )
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )

    instance.disconnect_server()

    assert commands == ["DISCONNECT"]
    assert disconnected == [True]
    assert instance.connected is False
    assert instance.game_started is False
    assert instance.connect_button.options["state"] == gui.tk.NORMAL
    assert instance.disconnect_button.options["state"] == gui.tk.DISABLED
    assert instance.port_entry.options["state"] == gui.tk.NORMAL
    assert instance.new_game_button.options["state"] == gui.tk.DISABLED
    assert instance.state_button.options["state"] == gui.tk.DISABLED
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in instance.square_buttons
    )
    assert instance.status_label.options["text"] == "Disconnected."
    assert instance.root.destroyed is False


@pytest.mark.parametrize("response", [None, "NACK:BADCMD"])
def test_disconnect_failure_is_not_reported_as_success(
    monkeypatch,
    response,
):
    instance = make_disconnectable_gui()
    instance.root = Root()
    commands = []
    disconnected = []
    errors = []
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: commands.append(command) or response,
    )
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )
    monkeypatch.setattr(
        gui.messagebox,
        "showerror",
        lambda *args: errors.append(args),
    )

    instance.disconnect_server()

    assert instance.connected is False
    assert instance.game_started is False
    assert instance.disconnect_button.options["state"] == gui.tk.DISABLED
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in instance.square_buttons
    )
    assert instance.root.destroyed is False
    assert commands == ["DISCONNECT"]
    assert disconnected == [True]
    assert instance.status_label.options["text"] != "Disconnected."
    assert errors[0][0] == "Disconnect Error"


def test_disconnect_handles_command_exception(monkeypatch):
    instance = make_disconnectable_gui()
    disconnected = []

    def raise_error(command):
        raise OSError("connection lost")

    monkeypatch.setattr(gui.serial_client, "send_command", raise_error)
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )
    monkeypatch.setattr(gui.messagebox, "showerror", lambda *args: None)

    instance.disconnect_server()

    assert instance.connected is False
    assert instance.game_started is False
    assert instance.disconnect_button.options["state"] == gui.tk.DISABLED
    assert all(
        button.options["state"] == gui.tk.DISABLED
        for button in instance.square_buttons
    )
    assert disconnected == [True]


def test_close_window_sends_disconnect_and_always_closes_window(
    monkeypatch,
):
    instance = make_disconnectable_gui()
    instance.root = Root()
    commands = []
    disconnected = []
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: commands.append(command) or "OK",
    )
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )

    instance.close_window()

    assert commands == ["DISCONNECT"]
    assert disconnected == [True]
    assert instance.root.destroyed is True
