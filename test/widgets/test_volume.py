import cairocffi
import pytest

from libqtile import bar, images
from libqtile.widget import Volume
from test.widgets.conftest import TEST_DIR, FakeBar


def test_images_fail():
    vol = Volume(theme_path=TEST_DIR)
    with pytest.raises(images.LoadingError):
        vol.setup_images()


def test_images_good(tmpdir, fake_bar, svg_img_as_pypath):
    names = (
        "audio-volume-high.svg",
        "audio-volume-low.svg",
        "audio-volume-medium.svg",
        "audio-volume-muted.svg",
    )
    for name in names:
        target = tmpdir.join(name)
        svg_img_as_pypath.copy(target)

    vol = Volume(theme_path=str(tmpdir))
    vol.bar = fake_bar
    vol.length_type = bar.STATIC
    vol.length = 0
    vol.setup_images()
    assert len(vol.surfaces) == len(names)
    for name, surfpat in vol.surfaces.items():
        assert isinstance(surfpat, cairocffi.SurfacePattern)


def test_emoji():
    vol = Volume(emoji=True)
    vol.volume = -1
    vol._update_drawer()
    assert vol.text == "\U0001f507"

    vol.volume = 29
    vol._update_drawer()
    assert vol.text == "\U0001f508"

    vol.volume = 79
    vol._update_drawer()
    assert vol.text == "\U0001f509"

    vol.volume = 80
    vol._update_drawer()
    assert vol.text == "\U0001f50a"

    vol.is_mute = True
    vol._update_drawer()
    assert vol.text == "\U0001f507"


def test_text():
    fmt = "Volume: {}"
    vol = Volume(fmt=fmt)
    vol.volume = -1
    vol._update_drawer()
    assert vol.text == "M"

    vol.volume = 50
    vol._update_drawer()
    assert vol.text == "50%"


def test_formats():
    unmute_format = "Volume: {volume}%"
    mute_format = "Volume: {volume}% M"
    vol = Volume(unmute_format=unmute_format, mute_format=mute_format)
    vol.volume = 50
    vol._update_drawer()
    assert vol.text == "Volume: 50%"

    vol.is_mute = True
    vol._update_drawer()
    assert vol.text == "Volume: 50% M"


def test_foregrounds(fake_qtile, fake_window):
    foreground = "#dddddd"
    mute_foreground = None

    vol = Volume(foreground=foreground, mute_foreground=mute_foreground)
    fakebar = FakeBar([vol], window=fake_window)
    vol._configure(fake_qtile, fakebar)

    vol.volume = 50
    vol._update_drawer()
    assert vol.layout.colour == foreground

    vol.mute_foreground = mute_foreground = "#888888"
    vol.is_mute = False
    vol._update_drawer()
    assert vol.layout.colour == foreground

    vol.is_mute = True
    vol._update_drawer()
    assert vol.layout.colour == mute_foreground
