# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 roger
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2015 Craig Barnes
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This module is kind of a hack; you've been warned :-). Some upstream work
# needs to happen in order to avoid doing this, though.
#
# The problem is that we want to use pango to draw stuff. We need to create a
# cairo surface, in particular an XCB surface. Since we're using xcffib as the
# XCB binding and there is no portable way to go from cffi's PyObject* cdata
# wrappers to the wrapped type [1], we can't add support to pycairo for XCB
# surfaces via xcffib.
#
# A similar problem exists one layer of indirection down with cairocffi --
# python's pangocairo is almost all C, and only works by including pycairo's
# headers and accessing members of structs only available in C, and not in
# python. Since cairocffi is pure python and also cffi based, we cannot extract
# the raw pointer to pass to the existing pangocairo bindings.
#
# The solution here is to implement a tiny pangocffi for the small set of pango
# functions we call. We're doing it directly here because we can, but it would
# not be difficult to use more upstream libraries (e.g. cairocffi and some
# pangocairocffi when it exists). This also allows us to drop pygtk entirely,
# since we are doing our own pango binding.
#
# [1]: https://groups.google.com/forum/#!topic/python-cffi/SPND0rRmazA
#
# This is not intended to be a complete cffi-based pango binding.


try:
    from libqtile._ffi_pango import ffi
except ImportError:
    raise ImportError("No module named libqtile._ffi_pango, be sure to run `python ./libqtile/ffi_build.py`")

gobject = ffi.dlopen('libgobject-2.0.so.0')
pango = ffi.dlopen('libpango-1.0.so.0')
pangocairo = ffi.dlopen('libpangocairo-1.0.so.0')


def patch_cairo_context(cairo_t):
    def create_layout():
        return PangoLayout(cairo_t._pointer)
    cairo_t.create_layout = create_layout

    def show_layout(layout):
        pangocairo.pango_cairo_show_layout(cairo_t._pointer, layout._pointer)
    cairo_t.show_layout = show_layout

    return cairo_t


ALIGN_CENTER = pango.PANGO_ALIGN_CENTER
ELLIPSIZE_END = pango.PANGO_ELLIPSIZE_END
units_from_double = pango.pango_units_from_double


class PangoLayout(object):
    def __init__(self, cairo_t):
        self._cairo_t = cairo_t
        self._pointer = pangocairo.pango_cairo_create_layout(cairo_t)

        def free(p):
            p = ffi.cast("gpointer", p)
            gobject.g_object_unref(p)
        self._pointer = ffi.gc(self._pointer, free)

    def finalize(self):
        self._desc = None
        self._pointer = None
        self._cairo_t = None

    def set_font_description(self, desc):
        # save a pointer so it doesn't get GC'd out from under us
        self._desc = desc
        pango.pango_layout_set_font_description(self._pointer, desc._pointer)

    def get_font_description(self):
        descr = pango.pango_layout_get_font_description(self._pointer)
        return FontDescription(descr)

    def set_alignment(self, alignment):
        pango.pango_layout_set_alignment(self._pointer, alignment)

    def set_attributes(self, attrs):
        pango.pango_layout_set_attributes(self._pointer, attrs)

    def set_text(self, text):
        text = text.encode('utf-8')
        pango.pango_layout_set_text(self._pointer, text, -1)

    def get_text(self):
        ret = pango.pango_layout_get_text(self._pointer)
        return ffi.string(ret).decode()

    def set_ellipsize(self, ellipzize):
        pango.pango_layout_set_ellipsize(self._pointer, ellipzize)

    def get_ellipsize(self):
        return pango.pango_layout_get_ellipsize(self._pointer)

    def get_pixel_size(self):
        width = ffi.new("int[1]")
        height = ffi.new("int[1]")

        pango.pango_layout_get_pixel_size(self._pointer, width, height)

        return width[0], height[0]

    def set_width(self, width):
        pango.pango_layout_set_width(self._pointer, width)


class FontDescription(object):
    def __init__(self, pointer=None):
        if pointer is None:
            self._pointer = pango.pango_font_description_new()
            self._pointer = ffi.gc(self._pointer, pango.pango_font_description_free)
        else:
            self._pointer = pointer

    @classmethod
    def from_string(cls, string):
        pointer = pango.pango_font_description_from_string(string.encode())
        pointer = ffi.gc(pointer, pango.pango_font_description_free)
        return cls(pointer)

    def set_family(self, family):
        pango.pango_font_description_set_family(self._pointer, family.encode())

    def get_family(self):
        ret = pango.pango_font_description_get_family(self._pointer)
        return ffi.string(ret).decode()

    def set_absolute_size(self, size):
        pango.pango_font_description_set_absolute_size(self._pointer, size)

    def set_size(self, size):
        pango.pango_font_description_set_size(self._pointer, size)

    def get_size(self):
        return pango.pango_font_description_get_size(self._pointer)


def parse_markup(value, accel_marker=0):
    attr_list = ffi.new("PangoAttrList**")
    text = ffi.new("char**")
    error = ffi.new("GError**")
    value = value.encode()

    ret = pango.pango_parse_markup(value, -1, accel_marker, attr_list, text, ffi.NULL, error)

    if ret == 0:
        raise Exception("parse_markup() failed for %s" % value)

    return attr_list[0], ffi.string(text[0]), chr(accel_marker)


def markup_escape_text(text):
    ret = gobject.g_markup_escape_text(text.encode('utf-8'), -1)
    return ffi.string(ret).decode()
