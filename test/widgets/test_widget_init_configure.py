# Copyright (c) 2021 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Widget specific tests

import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.widget as widgets
from libqtile.widget.base import ORIENTATION_BOTH, ORIENTATION_VERTICAL
from libqtile.widget.clock import Clock
from libqtile.widget.crashme import _CrashMe
from test.widgets.conftest import FakeBar

# This file runs a very simple test to check that widgets can be initialised
# and that keyword arguments are added to default values.
#
# This test is not meant to replace any widget specific tests but should catch
# any mistakes that inadvertently breakag widgets.
#
# By default, the test runs on every widget that is listed in __init__.py
# This is done by building a list called `parameters` which contains a tuple of
# (widget class, kwargs).
#
# Adjustments to the tests can be made below.

# Some widgets may require certain parameters to be set when initialising.
# Widgets listed here will replace the default values.
# This should be used as a last resort - any failure may indicate an
# underlying issue in the widget that should be resolved.
overrides = []

# Some widgets are not included in __init__.py
# They can be included in the tests by adding their details here
extras = [
    (_CrashMe, {}),  # Just used by devs but no harm checking it works
]

# To skip a test entirely, list the widget class here
no_test = [widgets.Mirror, widgets.PulseVolume]  # Mirror requires a reflection object

# To test a widget only under one backend, list the widget class here
exclusive_backend = {
    widgets.Systray: "x11",
}

################################################################################
# Do not edit below this line
################################################################################

# Build default list of all widgets and assign simple keyword argument
parameters = [(getattr(widgets, w), {"dummy_parameter": 1}) for w in widgets.__all__]

# Replace items in default list with overrides
for ovr in overrides:
    parameters = [ovr if ovr[0] == w[0] else w for w in parameters]

# Add the extra widgets
parameters.extend(extras)

# Remove items which need to be skipped
for skipped in no_test:
    parameters = [w for w in parameters if w[0] != skipped]


def no_op(*args, **kwargs):
    pass


@pytest.mark.parametrize("widget_class,kwargs", parameters)
def test_widget_init_config(manager_nospawn, minimal_conf_noscreen, widget_class, kwargs):
    if widget_class in exclusive_backend:
        if exclusive_backend[widget_class] != manager_nospawn.backend.name:
            pytest.skip("Unsupported backend")

    widget = widget_class(**kwargs)
    widget.draw = no_op

    # If widget inits ok then kwargs will now be attributes
    for k, v in kwargs.items():
        assert getattr(widget, k) == v

    # Test configuration
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([widget], 10))]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["top"].info()

    # Check widget is registered by checking names of widgets in bar
    assert i["widgets"][0]["name"] == widget.name


@pytest.mark.parametrize(
    "widget_class,kwargs",
    [
        param
        for param in parameters
        if param[0]().orientations in [ORIENTATION_BOTH, ORIENTATION_VERTICAL]
    ],
)
def test_widget_init_config_vertical_bar(
    manager_nospawn, minimal_conf_noscreen, widget_class, kwargs
):
    if widget_class in exclusive_backend:
        if exclusive_backend[widget_class] != manager_nospawn.backend.name:
            pytest.skip("Unsupported backend")

    widget = widget_class(**kwargs)
    widget.draw = no_op

    # If widget inits ok then kwargs will now be attributes
    for k, v in kwargs.items():
        assert getattr(widget, k) == v

    # Test configuration
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(left=libqtile.bar.Bar([widget], 10))]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["left"].info()

    # Check widget is registered by checking names of widgets in bar
    assert i["widgets"][0]["name"] == widget.name


def test_incompatible_orientation(fake_qtile, fake_window):
    clk1 = Clock()
    clk1.orientations = ORIENTATION_VERTICAL
    fakebar = FakeBar([clk1], window=fake_window)
    with pytest.raises(libqtile.confreader.ConfigError):
        clk1._configure(fake_qtile, fakebar)
