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

xcursors_ffi = FFI()
xcursors_ffi.set_source("liblavinder.core._ffi_xcursors", None)

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
    xcursors_ffi.compile()
