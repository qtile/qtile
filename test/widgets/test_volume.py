import pytest
from libqtile.widget import Volume
from libqtile import images
import cairocffi
from .conftest import TEST_DIR


def test_images_fail():
    vol = Volume(theme_path=TEST_DIR)
    with pytest.raises(images.LoadingError):
        vol.setup_images()


def test_images_good(tmpdir, fake_bar, svg_img_as_pypath):
    names = (
        'audio-volume-high.svg',
        'audio-volume-low.svg',
        'audio-volume-medium.svg',
        'audio-volume-muted.svg',
    )
    for name in names:
        target = tmpdir.join(name)
        svg_img_as_pypath.copy(target)

    vol = Volume(theme_path=str(tmpdir))
    vol.bar = fake_bar
    vol.setup_images()
    assert len(vol.surfaces) == len(names)
    for name, surfpat in vol.surfaces.items():
        assert isinstance(surfpat, cairocffi.SurfacePattern)
