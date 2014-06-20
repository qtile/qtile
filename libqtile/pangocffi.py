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

from cffi import FFI
import xcffib
import cairocffi
import commands

ffi = FFI()

ffi.include(xcffib.ffi)
ffi.include(cairocffi.ffi)

# pango/pangocairo
ffi.cdef("""
    #define PANGO_ALIGN_CENTER ...
    #define PANGO_SCALE ...
    #define PANGO_ELLIPSIZE_END ...

    typedef ... PangoContext;
    typedef ... PangoLayout;
    typedef ... PangoFontDescription;
    typedef ... PangoAttrList;
    typedef int PangoAlignment;

    typedef void* gpointer;
    typedef int gboolean;
    typedef ... gunichar;
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

def pkgconfig(*packages, **kw):
    flag_map = {'-I': 'include_dirs', '-L': 'library_dirs', '-l': 'libraries'}
    for token in commands.getoutput("pkg-config --libs --cflags %s" % ' '.join(packages)).split():
        if flag_map.has_key(token[:2]):
            kw.setdefault(flag_map.get(token[:2]), []).append(token[2:])
        else:
            # no need to -lpthread, we already have those symbols
            assert token == '-pthread'

    for k, v in kw.iteritems(): # remove duplicated
        kw[k] = list(set(v))
    return kw

compiler_args = pkgconfig('glib-2.0', 'pango', 'cairo', 'pangocairo')

C = ffi.verify("""
    #include <xcb/xcb.h>
    #include <xcb/xcbext.h>
    #include <cairo/cairo.h>
    #include <cairo/cairo-xcb.h>
    #include <pango/pango.h>
    #include <pango/pangocairo.h>

    // these we don't really need, but cairo on most distros is built for
    // support with them, so the macros are such that we have to include them.
    #include <cairo/cairo-pdf.h>
    #include <cairo/cairo-ps.h>
    #include <cairo/cairo-svg.h>
""", **compiler_args)

def CairoContext(cairo_t):
    def create_layout():
        return PangoLayout(cairo_t._pointer)
    cairo_t.create_layout = create_layout

    def show_layout(layout):
        C.pango_cairo_show_layout(cairo_t._pointer, layout._pointer)
    cairo_t.show_layout = show_layout

    return cairo_t

ALIGN_CENTER = C.PANGO_ALIGN_CENTER
SCALE = C.PANGO_SCALE
ELLIPSIZE_END = C.PANGO_ELLIPSIZE_END

def _const_char_to_py_str(cc):
    return ''.join(ffi.buffer(cc, len(cc)))

class PangoLayout(object):
    def __init__(self, cairo_t):
        self._cairo_t = cairo_t
        self._pointer = C.pango_cairo_create_layout(cairo_t)
        def free(p):
            p = ffi.cast("gpointer", p)
            C.g_object_unref(p)
        self._pointer = ffi.gc(self._pointer, free)

    def set_font_description(self, desc):
        # save a pointer so it doesn't get GC'd out from under us
        self._desc = desc
        C.pango_layout_set_font_description(self._pointer, desc._pointer)

    def get_font_description(self):
        descr = C.pango_layout_get_font_description(self._pointer)
        return FontDescription(descr)

    def set_alignment(self, alignment):
        C.pango_layout_set_alignment(self._pointer, alignment)

    def set_attributes(self, attrs):
        C.pango_layout_set_attributes(self._pointer, attrs._pointer)

    def set_text(self, text):
        text = text.encode('utf-8')
        C.pango_layout_set_text(self._pointer, text, -1)

    def get_text(self):
        ret = C.pango_layout_get_text(self._pointer)
        return _const_char_to_py_str(ret)

    def get_pixel_size(self):
        width = ffi.new("int[1]")
        height = ffi.new("int[1]")

        C.pango_layout_get_pixel_size(self._pointer, width, height)

        return width[0], height[0]

class FontDescription(object):
    def __init__(self, pointer=None):
        if pointer is None:
            self._pointer = C.pango_font_description_new()
            self._pointer = ffi.gc(self._pointer, C.pango_font_description_free)
        else:
            self._pointer = pointer

    def set_family(self, family):
        C.pango_font_description_set_family(self._pointer, family)

    def get_family(self):
        ret = C.pango_font_description_get_family(self._pointer)
        return _const_char_to_py_str(ret)

    def set_absolute_size(self, size):
        C.pango_font_description_set_absolute_size(self._pointer, size)

    def set_size(self, size):
        C.pango_font_description_set_size(self._pointer, size)

    def get_size(self, size):
        return C.pango_font_description_get_size(self._pointer, size)

def _free_deref(thing):
    C.free(thing[0])

def parse_markup(value):
    attr_list = ffi.new("PangoAttrList**")
    text = ffi.new("char**")
    error = ffi.new("GError**")

    ret = C.pango_parse_markup(value, -1, 0, attr_list, text, ffi.NULL, error)

    if ret:
        raise Exception("parse_markup() failed for %s" % value)
    attr_list = ffi.gc(attr_list, _free_deref)
    text = ffi.gc(attr_list, _free_deref)

    return attr_list, text
