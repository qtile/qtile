# This module is kind of a hack; you've been warned :-). Some upstream work
# needs to happen in order to avoid doing this, though.
#
# The problem is that we want to use pango to draw stuff. We need to create a
# cairo surface, in particular an XCB surface. Since we're using xcffib as the
# XCB binding and there is no way to go from cffi's PyObject* cdata wrappers to
# the wrapped type [1], we can't add support to pycairo for XCB surfaces via
# xcffib.
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
# pangocairocffi when it exists). This also allows us to drop pygtk and pycairo
# as dependencies, which is handy (and also reasonable, since we were basically
# using them as wrappers around one line C functions).
#
# [1]: https://groups.google.com/forum/#!topic/python-cffi/SPND0rRmazA

from cffi import FFI
import xcffib
import commands

ffi = FFI()

ffi.include(xcffib.ffi)

# cairo
ffi.cdef("""
    typedef ... cairo_surface_t;
    typedef ... cairo_t;
    typedef ... cairo_pattern_t;

    typedef struct {
        double x, y, width, height;
    } cairo_rectangle_t;

    cairo_surface_t *cairo_xcb_surface_create (xcb_connection_t *connection,
                                               xcb_drawable_t drawable,
                                               xcb_visualtype_t *visual,
                                               int width,
                                               int height);
    cairo_t *cairo_create (cairo_surface_t *target);

    void cairo_new_sub_path (cairo_t *cr);
    void cairo_arc (cairo_t *cr,
                    double xc,
                    double yc,
                    double radius,
                    double angle1,
                    double angle2);
    void cairo_close_path (cairo_t *cr);
    void cairo_stroke (cairo_t *cr);
    void cairo_fill (cairo_t *cr);
    void cairo_set_line_width (cairo_t *cr, double width);
    void cairo_rectangle (cairo_t *cr,
                          double x,
                          double y,
                          double width,
                          double height);
    cairo_pattern_t *cairo_pattern_create_linear (double x0,
                                                  double y0,
                                                  double x1,
                                                  double y1);
    void cairo_set_source (cairo_t *cr,
                           cairo_pattern_t *source);
    void cairo_set_source_rgba (cairo_t *cr,
                                double red,
                                double green,
                                double blue,
                                double alpha);
    // http://cairographics.org/manual/cairo-Paths.html
    // for move_to, line_to
""")

# pangocairo
ffi.cdef("""
    typedef ... PangoContext;
    typedef ... PangoLayout;
    typedef ... PangoFontDescription;

    PangoContext *pango_cairo_create_context (cairo_t *cr);
    PangoLayout *pango_cairo_create_layout (cairo_t *cr);
    // PangoLayout freed with g_object_unref()

    PangoFontDescription *pango_font_description_new (void);
    // freed with pango_font_description_free
""")

# "library"
ffi.cdef("""
    typedef ... pangocffi_context;

    pangocffi_context *mk_context(xcb_connection_t *connection, xcb_drawable_t drawable, xcb_visualtype_t *visual, int width, int height);
    void free_context(pangocffi_context *ctx);
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

libraries = compiler_args.pop('libraries')

C = ffi.verify("""
    #include <xcb/xcb.h>
    #include <xcb/xcbext.h>
    #include <cairo/cairo.h>
    #include <cairo/cairo-xcb.h>
    #include <pango/pango.h>
    #include <pango/pangocairo.h>

    typedef struct {
        PangoContext *pango;
        cairo_t *cairo;
        cairo_surface_t *surface;
    } pangocffi_context;

    pangocffi_context *mk_context(xcb_connection_t *connection, xcb_drawable_t drawable, xcb_visualtype_t *visual, int width, int height)
    {
        pangocffi_context* ctx = malloc(sizeof(pangocffi_context));

        ctx->surface = cairo_xcb_surface_create(connection, drawable, visual, width, height);
        // TODO: check for errors via cairo_surface_status ?

        ctx->cairo = cairo_create(ctx->surface);
        // TODO: check for errors via cairo_status ?

        ctx->pango = pango_cairo_create_context(ctx->cairo);
        // TODO: error checking?

        return ctx;
    }

    void free_context(pangocffi_context *ctx)
    {
        cairo_destroy(ctx->cairo);
        cairo_surface_destroy(ctx->surface);
        // ctx->pango
        free(ctx);
    }
""", libraries=libraries, compiler_args=compiler_args)
