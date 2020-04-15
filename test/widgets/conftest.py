import pytest
import os


@pytest.fixture(scope='function')
def fake_bar():
    from libqtile.bar import Bar
    height = 24
    b = Bar([], height)
    b.height = height
    return b


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(TEST_DIR), 'data')


@pytest.fixture(scope='module')
def svg_img_as_pypath():
    "Return the py.path object of a svg image"
    import py
    audio_volume_muted = os.path.join(
        DATA_DIR, 'svg', 'audio-volume-muted.svg',
    )
    audio_volume_muted = py.path.local(audio_volume_muted)
    return audio_volume_muted
