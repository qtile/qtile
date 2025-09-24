import pytest

import libqtile.bar
import libqtile.config
from libqtile import widget


def bad_importer(*args, **kwargs):
    raise ImportError()


@pytest.mark.parametrize("position", ["top", "bottom", "left", "right"])
def test_importerrorwidget(monkeypatch, manager_nospawn, minimal_conf_noscreen, position):
    """Check we get an ImportError widget with missing import?"""
    monkeypatch.setattr("libqtile.utils.importlib.import_module", bad_importer)

    badwidget = widget.TextBox("I am a naughty widget.")

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(**{position: libqtile.bar.Bar([badwidget], 10)})]

    manager_nospawn.start(config)

    testbar = manager_nospawn.c.bar[position]
    w = testbar.info()["widgets"][0]

    # Check that the widget has been replaced with an ImportError
    assert w["name"] == "importerrorwidget"
    assert w["text"] == "Import Error: TextBox"
