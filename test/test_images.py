from __future__ import division
import pytest
import libqtile.images as images
import cairocffi
import os
from os import path
from glob import glob

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
        assert img.file_type == ftype
        assert isinstance(img.surface, cairocffi.ImageSurface)
        assert img.file_type == ftype
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
        width0, height0 = img.width, img.height
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

    def test_setting_lock_aspect(self, png_img):
        img = png_img
        width0, height0 = img.width, img.height
        ratio = width0 / height0
        img.lock_aspect_ratio = True
        img.width = 4 * width0
        assert img.width == (4 * width0)
        assert (img.width / img.height) == pytest.approx(ratio)
        img.height = height0
        assert img.height == height0
        assert img.width == width0
        img.lock_aspect_ratio = False
        img.width = 5 * width0
        assert img.width == (5 * width0)
        assert img.height == height0

    def test_setting_negative_size(self, png_img):
        png_img.width = -90
        assert png_img.width == 1
        png_img.height = 0
        assert png_img.height == 1

    def test_pattern(self, path_n_bytes_image):
        path, bytes_image = path_n_bytes_image
        img = images.Img(bytes_image)
        assert isinstance(img.pattern, cairocffi.SurfacePattern)

    def test_pattern_resize(self, path_n_bytes_image):
        path, bytes_image = path_n_bytes_image
        img = images.Img.from_path(path)
        assert isinstance(img.pattern, cairocffi.SurfacePattern)
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (1.0, 0.0, 0.0, 1.0))
        img.width *= 2.0
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (0.5, 0.0, 0.0, 1.0))
        img.height = 3.0 * img.height
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (0.5, 0.0, 0.0, 1.0/3.0))

    def test_pattern_rotate(self, path_n_bytes_image):
        path, bytes_image = path_n_bytes_image
        img = images.Img(bytes_image)
        img.theta = 90.0
        assert img.theta == 90.0
        t_matrix = img.pattern.get_matrix().as_tuple()
        assert_approx_equal(t_matrix, (0.0, -1.0, 1.0, 0.0))
        img.theta = 45.0
        t_matrix = img.pattern.get_matrix().as_tuple()
        from math import sqrt
        s2o2 = sqrt(2) / 2.0
        assert_approx_equal(t_matrix, (s2o2, -s2o2, s2o2, s2o2))
        del img.theta
        assert img.theta == pytest.approx(0.0)
