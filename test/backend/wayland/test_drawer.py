from copy import copy
from unittest.mock import Mock

import cairocffi
import pytest

from libqtile import images
from libqtile.backend.wayland.drawer import Drawer
from test.test_images import SVGS, png_img_24, rgba_pixel_data  # noqa: F401


class FakeDrawer(Drawer):
    def __init__(self, image_surface, output_scale, monkeypatch):
        self._image_surface = image_surface
        win = Mock()
        win.scale = output_scale
        win.width = image_surface.get_width()
        win.height = image_surface.get_height()
        sentinel = object()
        win.surface = sentinel
        self._win = win
        self._width = image_surface.get_width()
        self._height = image_surface.get_height()
        self._reset_surface()

        real_from_pointer = cairocffi.Surface._from_pointer

        def fake_from_pointer(ptr, incref=False):
            if ptr is sentinel:
                return image_surface
            return real_from_pointer(ptr, incref)

        monkeypatch.setattr(cairocffi.Surface, "_from_pointer", staticmethod(fake_from_pointer))


@pytest.fixture(scope="function")
def svg_img():
    return images.Img.from_path(SVGS[0])


@pytest.fixture
def drawer(monkeypatch):
    image_surface = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, 24, 24)
    d = FakeDrawer(image_surface, 1.5, monkeypatch)
    return d, image_surface


# Lets assume icon size is 16 x 16 and output scale factor is 1.5. Therefore we
# want to draw the icon at 24 x 24 (16 x 1.5 = 24). if our icon has been scaled
# correctly, it will exactly match the original image
def test_hidpi_svg_scaling(svg_img, drawer):
    assert svg_img.width == 24
    assert svg_img.height == 24
    # Snapshot svg_img before any scaling
    img0 = copy(svg_img)
    # Set icon image size
    svg_img.resize(height=16)
    d, image_surface = drawer
    d.draw_image(svg_img)
    d._draw()
    assert bytes(img0.surface.get_data()) == bytes(image_surface.get_data())


def test_hidpi_png_scaling(png_img_24, drawer):  # noqa:F811
    assert png_img_24.width == 24
    assert png_img_24.height == 24
    img0 = copy(png_img_24)
    png_img_24.resize(height=16)
    d, image_surface = drawer
    d.draw_image(png_img_24)
    d._draw()
    assert bytes(img0.surface.get_data()) == bytes(image_surface.get_data())


def test_hidpi_pixel_data_scaling(rgba_pixel_data, drawer):  # noqa:F811
    img = images.Img.from_data(rgba_pixel_data, cairocffi.FORMAT_ARGB32, 24, 24)
    assert img.width == 24
    assert img.height == 24
    img0 = copy(img)
    img.resize(height=16)
    d, image_surface = drawer
    d.draw_image(img)
    d._draw()
    assert bytes(img0.surface.get_data()) == bytes(image_surface.get_data())


def test_hidpi_img_paint_mask(svg_img, drawer):
    assert svg_img.width == 24
    assert svg_img.height == 24
    # Snapshot svg_img before any scaling
    img0 = copy(svg_img)
    red_img0 = img0.paint_mask("#ff0000")
    # Set icon image size
    svg_img.resize(height=16)
    svg_img.paint_mask("#ff0000")
    d, image_surface = drawer
    d.draw_image(svg_img)
    d._draw()
    assert bytes(red_img0.surface.get_data()) == bytes(image_surface.get_data())
