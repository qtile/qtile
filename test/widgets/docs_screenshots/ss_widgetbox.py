import pytest

import libqtile.widget


@pytest.fixture
def widget(monkeypatch):
    # We create a wrapper for the WidgetBox which makes sure all widgets
    # inside the box have "has_mirrors" set to True as this keeps a copy of
    # the contents in the drawer which we can use for the screenshot.
    class WidgetBox(libqtile.widget.WidgetBox):
        def _configure(self, bar, screen):
            libqtile.widget.WidgetBox._configure(self, bar, screen)
            for w in self.widgets:
                w.drawer.has_mirrors = True

    yield WidgetBox


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {"widgets": [libqtile.widget.TextBox("Widget inside box.")]},
    ],
    indirect=True,
)
def ss_widgetbox(screenshot_manager):
    bar = screenshot_manager.c.bar["top"]

    # We can't just take a picture of the widget. We also need the area of the bar
    # that is revealed when the box is open.
    # As there are no other widgets here, we can just add up the length of all widgets.
    def bar_width():
        info = bar.info()
        widgets = info["widgets"]
        if not widgets:
            return 0

        return sum(x["length"] for x in widgets)

    def take_screenshot():
        target = screenshot_manager.target()
        bar.take_screenshot(target, width=bar_width())

    # Box is closed to start with
    take_screenshot()

    # Open the box to show contents
    screenshot_manager.c.widget["widgetbox"].toggle()
    take_screenshot()
