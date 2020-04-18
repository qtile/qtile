import cairocffi
import pytest

from libqtile import images
from libqtile.widget import Battery, BatteryIcon, battery
from libqtile.widget.battery import BatteryState, BatteryStatus
from test.widgets.conftest import TEST_DIR


class DummyBattery:
    def __init__(self, status):
        self._status = status

    def update_status(self):
        return self._status


class DummyErrorBattery:
    def __init__(self, **config):
        pass

    def update_status(self):
        raise RuntimeError("err")


def dummy_load_battery(bat):
    def load_battery(**config):
        return DummyBattery(bat)

    return load_battery


def test_text_battery_charging(monkeypatch):
    loaded_bat = BatteryStatus(
        state=BatteryState.CHARGING,
        percent=0.5,
        power=15.,
        time=1729,
    )

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery()

    text = batt.poll()
    assert text == "^ 50% 0:28 15.00 W"


def test_text_battery_discharging(monkeypatch):
    loaded_bat = BatteryStatus(
        state=BatteryState.DISCHARGING,
        percent=0.5,
        power=15.,
        time=1729,
    )

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery()

    text = batt.poll()
    assert text == "V 50% 0:28 15.00 W"


def test_text_battery_full(monkeypatch):
    loaded_bat = BatteryStatus(
        state=BatteryState.FULL,
        percent=0.5,
        power=15.,
        time=1729,
    )

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery()

    text = batt.poll()
    assert text == "Full"

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery(show_short_text=False)

    text = batt.poll()
    assert text == "= 50% 0:28 15.00 W"


def test_text_battery_empty(monkeypatch):
    loaded_bat = BatteryStatus(
        state=BatteryState.EMPTY,
        percent=0.5,
        power=15.,
        time=1729,
    )

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery()

    text = batt.poll()
    assert text == "Empty"

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery(show_short_text=False)

    text = batt.poll()
    assert text == "x 50% 0:28 15.00 W"

    loaded_bat = BatteryStatus(
        state=BatteryState.UNKNOWN,
        percent=0.,
        power=15.,
        time=1729,
    )

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery()

    text = batt.poll()
    assert text == "Empty"


def test_text_battery_unknown(monkeypatch):
    loaded_bat = BatteryStatus(
        state=BatteryState.UNKNOWN,
        percent=0.5,
        power=15.,
        time=1729,
    )

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery()

    text = batt.poll()
    assert text == "? 50% 0:28 15.00 W"


def test_text_battery_hidden(monkeypatch):
    loaded_bat = BatteryStatus(
        state=BatteryState.DISCHARGING,
        percent=0.5,
        power=15.,
        time=1729,
    )

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery(hide_threshold=0.6)

    text = batt.poll()
    assert text != ""

    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", dummy_load_battery(loaded_bat))
        batt = Battery(hide_threshold=0.4)

    text = batt.poll()
    assert text == ""


def test_text_battery_error(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(battery, "load_battery", DummyErrorBattery)
        batt = Battery()

    text = batt.poll()
    assert text == "Error: err"


def test_images_fail():
    """Test BatteryIcon() with a bad theme_path

    This theme path doesn't contain all of the required images.
    """
    batt = BatteryIcon(theme_path=TEST_DIR)
    with pytest.raises(images.LoadingError):
        batt.setup_images()


def test_images_good(tmpdir, fake_bar, svg_img_as_pypath):
    """Test BatteryIcon() with a good theme_path

    This theme path does contain all of the required images.
    """
    for name in BatteryIcon.icon_names:
        target = tmpdir.join(name + '.svg')
        svg_img_as_pypath.copy(target)

    batt = BatteryIcon(theme_path=str(tmpdir))
    batt.fontsize = 12
    batt.bar = fake_bar
    batt.setup_images()
    assert len(batt.surfaces) == len(BatteryIcon.icon_names)
    for name, surfpat in batt.surfaces.items():
        assert isinstance(surfpat, cairocffi.SurfacePattern)


def test_images_default(fake_bar):
    """Test BatteryIcon() with the default theme_path

    Ensure that the default images are successfully loaded.
    """
    batt = BatteryIcon()
    batt.fontsize = 12
    batt.bar = fake_bar
    batt.setup_images()
    assert len(batt.surfaces) == len(BatteryIcon.icon_names)
    for name, surfpat in batt.surfaces.items():
        assert isinstance(surfpat, cairocffi.SurfacePattern)
