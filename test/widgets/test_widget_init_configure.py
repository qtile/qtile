import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.widget as widgets
from libqtile.widget.crashme import _CrashMe

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
overrides = [
]

# Some widgets are not included in __init__.py
# They can be included in the tests by adding their details here
extras = [
    (_CrashMe, {}),  # Just used by devs but no harm checking it works
]

# To skip a test entirely, list the widget class here
no_test = [
    widgets.Mirror,  # Mirror requires a reflection object
    widgets.PulseVolume,
    widgets.KeyboardLayout,  # requires xkb-switch to be installed
]

################################################################################
# Do not edit below this line
################################################################################

# Build default list of all widgets and assign simple keyword argument
parameters = [
    (getattr(widgets, w), {"dummy_parameter": 1}) for w in widgets.__all__
]

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


class MinimalConf(libqtile.confreader.Config):
    auto_fullscreen = False
    keys = []
    mouse = []
    groups = [libqtile.config.Group("a")]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = []


@pytest.mark.parametrize("widget_class,kwargs", parameters)
def test_widget_init_config(manager_nospawn, widget_class, kwargs):
    widget = widget_class(**kwargs)
    widget.draw = no_op

    # If widget inits ok then kwargs will now be attributes
    for k, v in kwargs.items():
        assert getattr(widget, k) == v

    # Test configuration
    config = MinimalConf
    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar([widget], 10)
        )
    ]

    manager_nospawn.start(config)

    i = manager_nospawn.c.bar["top"].info()

    # Check widget is registered by checking names of widgets in bar
    allowed_names = [
        widget.name,
        "<no name>"  # systray is called "<no name>" as it subclasses _Window
    ]
    assert i["widgets"][0]["name"] in allowed_names
