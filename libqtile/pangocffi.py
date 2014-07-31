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

from __future__ import print_function

from cffi import FFI
import xcffib
import cairocffi

from .compat import getoutput, unichr

ffi = FFI()

ffi.include(xcffib.ffi)
ffi.include(cairocffi.ffi)

# pango/pangocairo
ffi.cdef("""
    typedef ... PangoContext;
    typedef ... PangoLayout;
    typedef ... PangoFontDescription;
    typedef ... PangoAttrList;
    typedef enum {
        PANGO_ALIGN_LEFT,
        PANGO_ALIGN_CENTER,
        PANGO_ALIGN_RIGHT
    } PangoAlignment;
    typedef enum {
        PANGO_ELLIPSEIZE_NONE,
        PANGO_ELLIPSIZE_START,
        PANGO_ELLIPSIZE_MIDDLE,
        PANGO_ELLIPSIZE_END
    } PangoEllipsizeMode;

    int
    pango_units_from_double (double d);

    typedef void* gpointer;
    typedef int gboolean;
    typedef unsigned int guint32;
    typedef guint32 gunichar;
    typedef ... GError;
    typedef int gint;

    void
    pango_cairo_show_layout (cairo_t *cr,
                             PangoLayout *layout);

    gboolean
    pango_parse_markup (const char *markup_text,
                        int length,
                        gunichar accel_marker,
                        PangoAttrList **attr_list,
                        char **text,
                        gunichar *accel_char,
                        GError **error);

    // https://developer.gnome.org/pango/stable/pango-Layout-Objects.html
    PangoLayout *pango_cairo_create_layout (cairo_t *cr);
    void g_object_unref(gpointer object);

    void
    pango_layout_set_font_description (PangoLayout *layout,
                                       const PangoFontDescription *desc);
    const PangoFontDescription *
    pango_layout_get_font_description (PangoLayout *layout);

    void
    pango_layout_set_alignment (PangoLayout *layout,
                                PangoAlignment alignment);
    void
    pango_layout_set_attributes (PangoLayout *layout,
                                 PangoAttrList *attrs);
    void
    pango_layout_set_text (PangoLayout *layout,
                           const char *text,
                           int length);
    const char *
    pango_layout_get_text (PangoLayout *layout);

    void
    pango_layout_get_pixel_size (PangoLayout *layout,
                                 int *width,
                                 int *height);

    void
    pango_layout_set_width (PangoLayout *layout,
                            int width);

    void
    pango_layout_set_ellipsize (PangoLayout *layout,
                                PangoEllipsizeMode  ellipsize);

    PangoEllipsizeMode
    pango_layout_get_ellipsize (PangoLayout *layout);

    // https://developer.gnome.org/pango/stable/pango-Fonts.html#PangoFontDescription
    PangoFontDescription *pango_font_description_new (void);
    void pango_font_description_free (PangoFontDescription *desc);

    void
    pango_font_description_set_family (PangoFontDescription *desc,
                                       const char *family);
    const char *
    pango_font_description_get_family (const PangoFontDescription *desc);

    void
    pango_font_description_set_absolute_size
                                   (PangoFontDescription *desc,
                                    double size);
    void
    pango_font_description_set_size (PangoFontDescription *desc,
                                     gint size);

    gint
    pango_font_description_get_size (const PangoFontDescription *desc);
""")

gobject = ffi.dlopen('gobject-2.0')
pango = ffi.dlopen('pango-1.0')
pangocairo = ffi.dlopen('pangocairo-1.0')

def CairoContext(cairo_t):
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

def _const_char_to_py_str(cc):
    return ''.join(ffi.buffer(cc, len(cc)))

class PangoLayout(object):
    def __init__(self, cairo_t):
        self._cairo_t = cairo_t
        self._pointer = pangocairo.pango_cairo_create_layout(cairo_t)
        def free(p):
            p = ffi.cast("gpointer", p)
            gobject.g_object_unref(p)
        self._pointer = ffi.gc(self._pointer, free)

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
        pango.pango_layout_set_attributes(self._pointer, attrs._pointer)

    def set_text(self, text):
        text = text.encode('utf-8')
        pango.pango_layout_set_text(self._pointer, text, -1)

    def get_text(self):
        ret = pango.pango_layout_get_text(self._pointer)
        return _const_char_to_py_str(ret)

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

    def set_family(self, family):
        pango.pango_font_description_set_family(self._pointer, family.encode())

    def get_family(self):
        ret = pango.pango_font_description_get_family(self._pointer)
        return _const_char_to_py_str(ret)

    def set_absolute_size(self, size):
        pango.pango_font_description_set_absolute_size(self._pointer, size)

    def set_size(self, size):
        pango.pango_font_description_set_size(self._pointer, size)

    def get_size(self, size):
        return pango.pango_font_description_get_size(self._pointer, size)

def parse_markup(value, accel_marker=0):
    attr_list = ffi.new("PangoAttrList**")
    text = ffi.new("char**")
    error = ffi.new("GError**")

    ret = pango.pango_parse_markup(value, -1, accel_marker, attr_list, text, ffi.NULL, error)

    if ret == 0:
        raise Exception("parse_markup() failed for %s" % value)

    return attr_list[0], ffi.string(text[0]), unichr(accel_marker)
