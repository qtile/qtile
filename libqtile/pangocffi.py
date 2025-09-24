from libqtile import DynamicLibraries, find_library
from libqtile.pango_ffi import pango_ffi as ffi

gobject = ffi.dlopen(find_library(DynamicLibraries.GOBJECT))  # type: ignore
pango = ffi.dlopen(find_library(DynamicLibraries.PANGO))  # type: ignore
pangocairo = ffi.dlopen(find_library(DynamicLibraries.PANGOCAIRO))  # type: ignore


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
units_to_double = pango.pango_units_to_double


ALIGNMENTS = {
    "left": pango.PANGO_ALIGN_LEFT,
    "center": pango.PANGO_ALIGN_CENTER,
    "right": pango.PANGO_ALIGN_RIGHT,
}


class PangoLayout:
    def __init__(self, cairo_t):
        self._cairo_t = cairo_t
        self._pointer = pangocairo.pango_cairo_create_layout(cairo_t)

        def free(p):
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
        text = text.encode("utf-8")
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


class FontDescription:
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


class BadMarkup(Exception):
    pass


def parse_markup(value, accel_marker=0):
    attr_list = ffi.new("PangoAttrList**")
    text = ffi.new("char**")
    error = ffi.new("GError**")
    markup_text = value.encode()

    ret = pango.pango_parse_markup(
        markup_text, -1, accel_marker, attr_list, text, ffi.NULL, error
    )

    if ret == 0:
        raise BadMarkup(f"parse_markup() failed for: {value}")

    return attr_list[0], ffi.string(text[0]), chr(accel_marker)


def markup_escape_text(text):
    ret = gobject.g_markup_escape_text(text.encode("utf-8"), -1)
    return ffi.string(ret).decode()
