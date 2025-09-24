import pytest

import libqtile
from libqtile.command.base import expose_command
from libqtile.confreader import Config
from libqtile.layout.base import _SimpleLayoutBase


class DummyLayout(_SimpleLayoutBase):
    defaults = [
        ("current_offset", 0, ""),
        ("current_position", None, ""),
    ]

    def __init__(self, **config):
        _SimpleLayoutBase.__init__(self, **config)
        self.add_defaults(DummyLayout.defaults)

    def add_client(self, client):
        return super().add_client(
            client, offset_to_current=self.current_offset, client_position=self.current_position
        )

    def configure(self, client, screen_rect):
        pass

    @expose_command("up")
    def previous(self):
        _SimpleLayoutBase.previous()

    @expose_command("down")
    def next(self):
        _SimpleLayoutBase.next()


class BaseLayoutConfigBottom(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [DummyLayout(current_position="bottom")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


class BaseLayoutConfigTop(Config):
    auto_fullscreen = True
    groups = [libqtile.config.Group("a")]
    layouts = [DummyLayout(current_position="top")]
    floating_layout = libqtile.resources.default_config.floating_layout
    keys = []
    mouse = []
    screens = []


baselayoutconfigbottom = pytest.mark.parametrize(
    "manager", [BaseLayoutConfigBottom], indirect=True
)
baselayoutconfigtop = pytest.mark.parametrize("manager", [BaseLayoutConfigTop], indirect=True)


@baselayoutconfigbottom
def test_base_client_position_bottom(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["clients"] == ["one", "two"]


@baselayoutconfigtop
def test_base_client_position_top(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert manager.c.layout.info()["clients"] == ["two", "one"]
