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


@pytest.fixture
def active_gui():
    instance = gui.TicTacToeGUI.__new__(gui.TicTacToeGUI)
    instance.connected = True
    instance.game_started = True
    instance.board = ["."] * 9
    instance.current_player = "X"
    instance.status_label = StatusLabel()
    instance.update_board = lambda: None
    return instance


@pytest.mark.parametrize(
    ("response", "expected_status"),
    [
        ("NACK:NOTURN", "It's not your turn!"),
        ("OK:BOARD:invalid", "Invalid board from server."),
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

    active_gui.make_move(4)

    assert active_gui.board == ["."] * 9
    assert active_gui.current_player == "X"
    assert active_gui.game_started is True
    assert active_gui.status_label.options["text"] == expected_status


def test_communication_error_allows_reconnection(active_gui, monkeypatch):
    active_gui.connect_button = Widget()
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
    assert active_gui.port_entry.options["state"] == gui.tk.NORMAL
    assert active_gui.new_game_button.options["state"] == gui.tk.DISABLED
    assert active_gui.state_button.options["state"] == gui.tk.DISABLED
    assert disconnected == [True]


def test_close_window_sends_disconnect_and_releases_transport(
    active_gui,
    monkeypatch,
):
    class Root:
        destroyed = False

        def destroy(self):
            self.destroyed = True

    active_gui.root = Root()
    commands = []
    disconnected = []
    monkeypatch.setattr(
        gui.serial_client,
        "send_command",
        lambda command: commands.append(command),
    )
    monkeypatch.setattr(
        gui.serial_client,
        "disconnect",
        lambda: disconnected.append(True),
    )

    active_gui.close_window()

    assert commands == ["DISCONNECT"]
    assert disconnected == [True]
    assert active_gui.root.destroyed is True
