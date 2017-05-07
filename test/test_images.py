"""
test_images.py contains unittests for libqtile.images.Img
and its supporting code.
"""
from __future__ import division
import pytest
import libqtile.images as images
import cairocffi
import os
from os import path
from glob import glob
from collections import OrderedDict

TEST_DIR = path.dirname(os.path.abspath(__file__))
DATA_DIR = path.join(TEST_DIR, 'data')
PNGS = glob(path.join(DATA_DIR, '*', '*.png'))
SVGS = glob(path.join(DATA_DIR, '*', '*.svg'))
ALL_IMAGES = glob(path.join(DATA_DIR, '*', '*'))

@pytest.fixture(
    scope='function',
    params=ALL_IMAGES,
)
def path_n_bytes_image(request):
    fpath = request.param
    with open(fpath, 'rb') as fobj:
        bobj = fobj.read()
    return fpath, bobj

@pytest.fixture(
    scope='function',
    params=PNGS,
)
def path_n_bytes_image_pngs(request):
    fpath = request.param
    with open(fpath, 'rb') as fobj:
        bobj = fobj.read()
    return fpath, bobj

@pytest.fixture(scope='function')
def png_img():
    return images.Img.from_path(PNGS[0])

def test_get_cairo_surface(path_n_bytes_image):
    path, bytes_image = path_n_bytes_image
    surf_info = images.get_cairo_surface(bytes_image)
    assert isinstance(surf_info.surface, cairocffi.ImageSurface)
    assert path.split('.')[-1].lower() == surf_info.file_type

def test_get_cairo_surface_bad_input():
    with pytest.raises(images.LoadingError):
        surf = images.get_cairo_surface(b'asdfasfdi3')

def assert_approx_equal(vec0, vec1):
    approx = pytest.approx
    for val0, val1 in zip(vec0, vec1):
        assert val0 == approx(val1)

class TestImg(object):
    def test_init(self, path_n_bytes_image):
        path, bytes_image = path_n_bytes_image
        img = images.Img(bytes_image)
        ftype = path.split('.')[-1].lower()
        assert isinstance(img.surface, cairocffi.ImageSurface)
        del img.surface
        assert isinstance(img.surface, cairocffi.ImageSurface)

    def test_from_path(self, path_n_bytes_image):
        path, bytes_image = path_n_bytes_image
        img = images.Img(bytes_image)
        assert isinstance(img.surface, cairocffi.ImageSurface)
        img2 = img.from_path(path)
        assert img == img2
        img2.theta = 90.0
        assert img != img2
        img2.theta = 0.0
        assert img == img2

    def test_setting(self, png_img):
        img = png_img
        width0, height0 = img.default_size
        pat0 = img.pattern
        img.width = width0 + 3
        assert pat0 != img.pattern
        assert img.width == (width0 + 3)
        pat1 = img.pattern
        img.height = height0 + 7
        assert img.height == (height0 + 7)
        assert img.pattern != pat0
        assert img.pattern != pat1
        pat2 = img.pattern
        img.theta = -35.0
        assert img.pattern != pat0
        assert img.pattern != pat1
        assert img.pattern != pat2
        assert img.theta == pytest.approx(-35.0)

    def test_equality(self, png_img):
        width0, height0 = png_img.default_size
        png_img2 = images.Img.from_path(png_img.path)
        assert png_img == png_img2
        png_img.width = width0 * 2
        png_img2.height = width0 * 2
        assert png_img != png_img2

    def test_setting_negative_size(self, png_img):
        png_img.width = -90
        assert png_img.width == 1
        png_img.height = 0
        assert png_img.height == 1

    def test_pattern(self, path_n_bytes_image):
        path, bytes_image = path_n_bytes_image
        img = images.Img(bytes_image)
        assert isinstance(img.pattern, cairocffi.SurfacePattern)

    def test_pattern_resize(self, path_n_bytes_image_pngs):
        path, bytes_image = path_n_bytes_image_pngs
        img = images.Img.from_path(path)
        assert isinstance(img.pattern, cairocffi.SurfacePattern)
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (1.0, 0.0, 0.0, 1.0))
        img.width = 2.0 * img.default_size.width
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (0.5, 0.0, 0.0, 1.0))
        img.height = 3.0 * img.default_size.height
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (0.5, 0.0, 0.0, 1.0/3.0))

    def test_pattern_rotate(self, path_n_bytes_image):
        path, bytes_image = path_n_bytes_image
        img = images.Img(bytes_image)
        img.theta = 90.0
        assert img.theta == 90.0
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (0.0, 1.0, -1.0, 0.0))
        img.theta = 45.0
        t_matrix = img.pattern.get_matrix().as_tuple()
        from math import sqrt
        s2o2 = sqrt(2) / 2.0
        assert_approx_equal(t_matrix, (s2o2, s2o2, -s2o2, s2o2))
        del img.theta
        assert img.theta == pytest.approx(0.0)

class TestImgScale(object):
    def test_scale(self, png_img):
        size = png_img.default_size
        png_img.scale(2, 3)
        assert png_img.width == 2 * size.width
        assert png_img.height == 3 * size.height

    def test_scale_rounding(self, png_img):
        size = png_img.default_size
        png_img.scale(1.99999, 2.99999)
        assert png_img.width == 2 * size.width
        assert png_img.height == 3 * size.height

    def test_scale_width_lock(self, png_img):
        size = png_img.default_size
        png_img.scale(width_factor=10, lock_aspect_ratio=True)
        assert png_img.width == 10 * size.width
        assert png_img.height == 10 * size.height

    def test_scale_height_lock(self, png_img):
        size = png_img.default_size
        png_img.scale(height_factor=11, lock_aspect_ratio=True)
        assert png_img.height == 11 * size.height
        assert png_img.width == 11 * size.width

    def test_scale_fail_lock(self, png_img):
        with pytest.raises(ValueError):
            png_img.scale(0.5, 4.0, lock_aspect_ratio=True)

    def test_scale_fail(self, png_img):
        with pytest.raises(ValueError):
            png_img.scale()

class TestImgResize(object):
    def test_resize(self, png_img):
        png_img.resize(100, 100)
        assert png_img.width == 100
        assert png_img.height == 100

    def test_resize_width(self, png_img):
        size = png_img.default_size
        ratio = size.width / size.height
        png_img.resize(width=40)
        assert png_img.width == 40
        assert (png_img.width / png_img.height) == pytest.approx(ratio)

    def test_resize_height(self, png_img):
        size = png_img.default_size
        ratio = size.width / size.height
        png_img.resize(height=10)
        assert png_img.height == 10
        assert (png_img.width / png_img.height) == pytest.approx(ratio)


class TestGetMatchingFiles(object):
    def test_audio_volume_muted(self):
        name = 'audio-volume-muted'
        dfiles = images.get_matching_files(
            DATA_DIR,
            False,
            name,
        )
        result = dfiles[name]
        assert len(result) == 2
        png = path.join(DATA_DIR, 'png', 'audio-volume-muted.png')
        assert png in result
        svg = path.join(DATA_DIR, 'svg', 'audio-volume-muted.svg')
        assert svg in result

    def test_only_svg(self):
        name = 'audio-volume-muted.svg'
        dfiles = images.get_matching_files(
            DATA_DIR,
            True,
            name,
        )
        result = dfiles[name]
        assert len(result) == 1
        svg = path.join(DATA_DIR, 'svg', 'audio-volume-muted.svg')
        assert svg in result

    def test_multiple(self):
        names = OrderedDict()
        names['audio-volume-muted'] = 2
        names['battery-caution-charging'] = 1
        dfiles = images.get_matching_files(DATA_DIR, False, *names)
        for name, length in names.items():
            assert len(dfiles[name]) == length


class TestLoader(object):
    @pytest.fixture(scope='function')
    def loader(self):
        png_dir = path.join(DATA_DIR, 'png')
        svg_dir = path.join(DATA_DIR, 'svg')
        return images.Loader(svg_dir, png_dir)

    def test_audio_volume_muted(self, loader):
        name = 'audio-volume-muted'
        result = loader(name)
        assert isinstance(result[name], images.Img)
        assert result[name].path.endswith('.svg')

    def test_audio_volume_muted_png(self, loader):
        name = 'audio-volume-muted.png'
        loader.explicit_filetype = True
        result = loader(name)
        assert isinstance(result[name], images.Img)
        assert result[name].path.endswith('.png')

    def test_load_file_missing(self, loader):
        names = ('audio-asdlfjasdvolume-muted', 'audio-volume-muted')
        with pytest.raises(images.LoadingError):
            result = loader(*names)
