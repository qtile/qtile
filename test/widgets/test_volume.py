import pytest
import py
import os
from libqtile.widget import Volume
from libqtile import images
import cairocffi

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(TEST_DIR), 'data')

audio_volume_muted = os.path.join(
    DATA_DIR, 'svg', 'audio-volume-muted.svg',
)

audio_volume_muted = py.path.local(audio_volume_muted)

def test_images_fail():
    vol = Volume(theme_path=TEST_DIR)
    with pytest.raises(images.LoadingError):
        vol.setup_images()

def test_images_good(tmpdir, bar):
    names = (
        'audio-volume-high.svg',
        'audio-volume-low.svg',
        'audio-volume-medium.svg',
        'audio-volume-muted.svg',
    )
    for name in names:
        target = tmpdir.join(name)
        audio_volume_muted.copy(target)

    vol = Volume(theme_path=str(tmpdir))
    vol.bar = bar
    vol.setup_images()
    assert len(vol.surfaces) == len(names)
    for name, surfpat in vol.surfaces.items():
        assert isinstance(surfpat, cairocffi.SurfacePattern)
