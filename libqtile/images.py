from __future__ import division
import cairocffi
import cairocffi.pixbuf
import io
import os
from collections import namedtuple as _namedtuple

class LoadingError(Exception):
    pass

_SurfaceInfo = _namedtuple('_SurfaceInfo', ('surface', 'file_type'))
def get_cairo_surface(bytes_img):
    try:
        surf = cairocffi.ImageSurface.create_from_png(io.BytesIO(bytes_img))
        return _SurfaceInfo(surf, 'png')
    except (MemoryError, OSError):
        pass
    try:
        surf, fmt = cairocffi.pixbuf.decode_to_image_surface(bytes_img)
        return _SurfaceInfo(surf, fmt)
    except cairocffi.pixbuf.ImageLoadingError:
        pass
    raise LoadingError("Couldn't load image!")

def get_cairo_pattern(surface, width, height, theta=0.0):
    """Return a SurfacePattern from an ImageSurface.

    if width and height are not None scale the pattern
    to be size width and height.

    theta is in degrees ccw
    """
    EPSILON = 1.0e-6
    from math import pi

    if surface is None:
        return None
    pattern = cairocffi.SurfacePattern(surface)
    pattern.set_filter(cairocffi.FILTER_BEST)
    matrix = cairocffi.Matrix()
    # TODO cleanup this function
    tr_width, tr_height = None, None
    if (width is not None) and (width != surface.get_width()):
        tr_width = surface.get_width() / width
    if (height is not None) and (height != surface.get_height()):
        tr_height = surface.get_height() / height
    if (tr_width is not None) or (tr_height is not None):
        tr_width = tr_width if tr_width is not None else 1.0
        tr_height = tr_height if tr_height is not None else 1.0
        matrix.scale(tr_width, tr_height)

    if abs(theta) > EPSILON:
        theta_rad = pi / 180.0 * theta
        mat_rot = cairocffi.Matrix.init_rotate(-theta_rad)
        matrix = mat_rot.multiply(matrix)

    pattern.set_matrix(matrix)
    return pattern


class Img(object):
    """Img is a class which creates & manipulates cairo SurfacePatterns from an image

    There are two constructors Img(...) and Img.from_path(...)

    The cairo surface pattern is at img.pattern.
    Changing any of the attributes width, height, or theta will update the pattern.

    - width :: pattern width in pixels
    - height :: pattern height in pixels
    - theta :: rotation of pattern counter clockwise in degrees
    Pattern is first stretched, then rotated.

    - lock_aspect_ratio :: maintain aspect ratio when changing height or width
    """
    def __init__(self, bytes_img, name='', path='', lock_aspect_ratio=False):
        self.lock_aspect_ratio = lock_aspect_ratio
        self.bytes_img = bytes_img
        self.name = name
        self.path = path

    @classmethod
    def from_path(cls, image_path):
        "Create an Img instance from image_path"
        with open(image_path, 'rb') as fobj:
            bytes_img = fobj.read()
        name = os.path.basename(image_path)
        name, file_type = os.path.splitext(name)
        file_type = file_type.lstrip('.')
        return cls(bytes_img, name=name, path=image_path)

    @property
    def file_type(self):
        try:
            return self._file_type
        except AttributeError:
            self.surface
            return self._file_type

    @property
    def surface(self):
        try:
            return self._surface
        except AttributeError:
            surf, fmt = get_cairo_surface(self.bytes_img)
            self._surface = surf
            self._file_type = fmt
            return surf

    @surface.deleter
    def surface(self):
        del self._surface
        del self.pattern

    @property
    def theta(self):
        try:
            return self._theta
        except AttributeError:
            return 0.0

    @theta.setter
    def theta(self, value):
        self._theta = float(value)
        del self.pattern

    @theta.deleter
    def theta(self):
        del self._theta
        del self.pattern

    @property
    def width(self):
        try:
            return self._width
        except AttributeError:
            return self.surface.get_width()

    @width.setter
    def width(self, value):
        new_width = max(int(value), 1)
        if self.lock_aspect_ratio:
            height0, width0 = self.height, self.width
            self._height = int(height0 * new_width / width0)
        self._width = new_width
        del self.pattern

    @width.deleter
    def width(self):
        del self._width
        del self.pattern

    @property
    def height(self):
        try:
            return self._height
        except AttributeError:
            return self.surface.get_height()

    @height.setter
    def height(self, value):
        new_height = max(int(value), 1)
        if self.lock_aspect_ratio:
            height0, width0 = self.height, self.width
            self._width = int(width0 * new_height / height0)
        self._height = new_height
        del self.pattern

    @height.deleter
    def height(self):
        del self._height
        del self.pattern

    @property
    def pattern(self):
        try:
            return self._pattern
        except AttributeError:
            pat = get_cairo_pattern(self.surface, self.width, self.height, self.theta)
            self._pattern = pat
            return pat

    @pattern.deleter
    def pattern(self):
        try:
            del self._pattern
        except AttributeError:
            pass

    def __repr__(self):
        return '<{cls_name}: {name!r}, {width}x{height}@{theta:.1f}deg, {path!r}>'.format(
            cls_name=self.__class__.__name__,
            name=self.name,
            width=self.width,
            height=self.height,
            path=self.path,
            theta=self.theta,
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        s0 = set((self.bytes_img, self.theta, self.width, self.height))
        s1 = set((other.bytes_img, other.theta, other.width, other.height))
        return s0 == s1
