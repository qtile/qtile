from libqtile import hook
from libqtile.bar import Bar
from libqtile.widget import WindowCount


class FakeWindowList:
    def __init__(self):
        self.windows = []


class FakeQtile:
    def __init__(self):
        self.groups = {1: FakeWindowList(), 0: FakeWindowList()}
        self._current_group = 1

    def add_window(self):
        self.groups[self._current_group].windows.append("window")
        hook.fire("client_managed", "window")

    def close_window(self):
        try:
            self.groups[self._current_group].windows.pop()
            hook.fire("client_killed", "window")
        except IndexError:
            pass

    def switch_group(self):
        self._current_group = (self._current_group + 1) % 2
        hook.fire("setgroup")

    def draw(self):
        pass

    @property
    def current_group(self):
        return self.groups[self._current_group]


def test_window_count():
    wc = WindowCount()
    fakebar = Bar([wc], 24)
    wc.bar = fakebar
    qtile = FakeQtile()
    wc.qtile = qtile
    wc._setup_hooks()

    # No windows opened
    assert wc._count == 0

    # Add a window and check count
    qtile.add_window()
    assert wc._count == 1

    # Add a window and check text
    qtile.add_window()
    assert wc.text == "2"

    # Change to empty group
    qtile.switch_group()
    assert wc._count == 0

    # Change back to group
    qtile.switch_group()
    assert wc._count == 2

    # Close all windows and check count is 0 and widget not displayed
    qtile.close_window()
    qtile.close_window()
    assert wc._count == 0
    assert wc.calculate_length() == 0
