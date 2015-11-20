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

from cffi import FFI
from xcffib.ffi_build import ffi as xcffib_ffi
from cairocffi.ffi_build import ffi as cairocffi_ffi

pango_ffi = FFI()
# PyPy < 2.6 compatibility
if hasattr(pango_ffi, 'set_source'):
    pango_ffi.set_source("libqtile._ffi_pango", None)

pango_ffi.include(cairocffi_ffi)

pango_ffi.cdef("""
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
    typedef char gchar;
    typedef signed long gssize;
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

    PangoFontDescription *
    pango_font_description_from_string (const char *str);

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

    // https://developer.gnome.org/glib/stable/glib-Simple-XML-Subset-Parser.html
    gchar *
    g_markup_escape_text(const gchar *text,
                         gssize length);
""")

xcursors_ffi = FFI()
# PyPy < 2.6 compatibility
if hasattr(xcursors_ffi, 'set_source'):
    xcursors_ffi.set_source("libqtile._ffi_xcursors", None)

xcursors_ffi.include(xcffib_ffi)

xcursors_ffi.cdef("""
    typedef uint32_t xcb_cursor_t;
    typedef struct xcb_cursor_context_t xcb_cursor_context_t;

    int xcb_cursor_context_new(
        xcb_connection_t *conn,
        xcb_screen_t *screen,
        xcb_cursor_context_t **ctx
        );

    xcb_cursor_t xcb_cursor_load_cursor(
        xcb_cursor_context_t *ctx,
        const char *name
        );

    void xcb_cursor_context_free(xcb_cursor_context_t *ctx);
""")

if __name__ == "__main__":
    pango_ffi.compile()
    xcursors_ffi.compile()
