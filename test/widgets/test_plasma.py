import pytest

from libqtile import layout
from libqtile.config import Bar, Screen
from libqtile.confreader import Config
from libqtile.widget import plasma


@pytest.fixture(scope="function")
def plasma_manager(manager_nospawn, request):
    class PlasmaConfig(Config):
        layouts = [layout.Plasma()]
        screens = [Screen(top=Bar([plasma.Plasma(**getattr(request, "param", dict()))], 30))]

    manager_nospawn.start(PlasmaConfig)

    yield manager_nospawn


def config(**kwargs):
    return pytest.mark.parametrize("plasma_manager", [kwargs], indirect=True)


def test_plasma_defaults(plasma_manager):
    def text():
        return plasma_manager.c.widget["plasma"].info()["text"]

    layout = plasma_manager.c.layout

    assert text() == " H"

    layout.mode_vertical()
    assert text() == " V"

    layout.mode_horizontal_split()
    assert text() == "HS"

    layout.mode_vertical_split()
    assert text() == "VS"


@config(horizontal="-", vertical="|", horizontal_split="=", vertical_split="||", format="{mode}")
def test_custom_text(plasma_manager):
    def text():
        return plasma_manager.c.widget["plasma"].info()["text"]

    layout = plasma_manager.c.layout

    assert text() == "-"

    layout.mode_vertical()
    assert text() == "|"

    layout.mode_horizontal_split()
    assert text() == "="

    layout.mode_vertical_split()
    assert text() == "||"


@config(format="{mode}")
def test_window_focus_change(plasma_manager):
    def text():
        return plasma_manager.c.widget["plasma"].info()["text"]

    def win(name):
        idx = [w["id"] for w in plasma_manager.c.windows() if w["name"] == name]
        assert idx
        return plasma_manager.c.window[idx[0]]

    layout = plasma_manager.c.layout

    assert text() == "H"
    plasma_manager.test_window("one")
    plasma_manager.test_window("two")

    layout.mode_vertical()
    plasma_manager.test_window("three")
    assert text() == "H"

    win("one").focus()
    assert text() == "V"

    win("three").focus()
    assert text() == "H"

    win("two").focus()
    assert text() == "H"

    win("one").focus()
    assert text() == "V"


@config(format="{mode}")
def test_mode_change(plasma_manager):
    def text():
        return plasma_manager.c.widget["plasma"].info()["text"]

    assert text() == "H"

    for mode in ["HS", "V", "VS", "H"]:
        plasma_manager.c.widget["plasma"].next_mode()
        assert text() == mode

    for mode in ["HS", "V", "VS", "H"]:
        plasma_manager.c.bar["top"].fake_button_press(0, 0, 1)
        assert text() == mode
