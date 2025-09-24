from cffi import FFI
from xcffib.ffi import ffi as xcffib_ffi

xcursors_ffi = FFI()

xcursors_ffi.include(xcffib_ffi)

xcursors_ffi.cdef(
    """
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
"""
)
