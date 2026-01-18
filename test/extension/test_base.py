import pytest

from libqtile.extension.base import RunCommand, _Extension

parameters = [
    ("#000", "#000"),
    ("#000000", "#000000"),
    ("000", "#000"),
    ("000000", "#000000"),
    ("#0000", None),
    ("0000", None),
    (0, None),
]


@pytest.mark.parametrize("value,expected", parameters)
def test_valid_colours(value, expected):
    extension = _Extension(foreground=value)
    extension._configure(None)
    assert extension.foreground == expected


def test_valid_colours_extension_defaults(monkeypatch):
    defaults = {
        "foreground": "00ff00",
        "background": "000000",
        "selected_foreground": "000000",
        "selected_background": "00ff00",
    }
    extension = _Extension(foreground="0000ff")

    # Set defaults after widget is created to mimic behaviour of extension being
    # initialised in config.
    monkeypatch.setattr(_Extension, "global_defaults", defaults)
    extension._configure(None)
    assert extension.foreground == "#0000ff"
    assert extension.background == "#000000"
    assert extension.selected_foreground == "#000000"
    assert extension.selected_background == "#00ff00"


def test_base_methods():
    class FakeQtile:
        pass

    qtile = FakeQtile()
    extension = _Extension()
    extension._configure(qtile)

    assert extension.qtile is qtile

    with pytest.raises(NotImplementedError):
        extension.run()


def test_run_command(monkeypatch):
    def fake_popen(cmd, *args, **kwargs):
        return cmd

    monkeypatch.setattr("libqtile.extension.base.Popen", fake_popen)

    extension = RunCommand(command="command --arg1 --arg2")

    assert extension.command == "command --arg1 --arg2"
    assert extension.run() == "command --arg1 --arg2"
