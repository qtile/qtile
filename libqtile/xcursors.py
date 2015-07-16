from logging import getLogger

# PyPy < 2.6 compaitibility
try:
    from ._ffi_xcursors import ffi
except ImportError:
    from .ffi_build import xcursors_ffi as ffi


# Stolen from samurai-x
# (Don't know where to put it, so I'll put it here)
# XCB cursors doesn't want to be themed, libxcursor
# would be better choice I think
# and we (indirectly) depend on it anyway...
class Cursors(dict):
    def __init__(self, conn):
        self.conn = conn
        self.log = getLogger('qtile')

        cursors = (
            (b'X_cursor', 0),
            (b'arrow', 2),
            (b'based_arrow_down', 4),
            (b'based_arrow_up', 6),
            (b'boat', 8),
            (b'bogosity', 10),
            (b'bottom_left_corner', 12),
            (b'bottom_right_corner', 14),
            (b'bottom_side', 16),
            (b'bottom_tee', 18),
            (b'box_spiral', 20),
            (b'center_ptr', 22),
            (b'circle', 24),
            (b'clock', 26),
            (b'coffee_mug', 28),
            (b'cross', 30),
            (b'cross_reverse', 32),
            (b'crosshair', 34),
            (b'diamond_cross', 36),
            (b'dot', 38),
            (b'dotbox', 40),
            (b'double_arrow', 42),
            (b'draft_large', 44),
            (b'draft_small', 46),
            (b'draped_box', 48),
            (b'exchange', 50),
            (b'fleur', 52),
            (b'gobbler', 54),
            (b'gumby', 56),
            (b'hand1', 58),
            (b'hand2', 60),
            (b'heart', 62),
            (b'icon', 64),
            (b'iron_cross', 66),
            (b'left_ptr', 68),
            (b'left_side', 70),
            (b'left_tee', 72),
            (b'leftbutton', 74),
            (b'll_angle', 76),
            (b'lr_angle', 78),
            (b'man', 80),
            (b'middlebutton', 82),
            (b'mouse', 84),
            (b'pencil', 86),
            (b'pirate', 88),
            (b'plus', 90),
            (b'question_arrow', 92),
            (b'right_ptr', 94),
            (b'right_side', 96),
            (b'right_tee', 98),
            (b'rightbutton', 100),
            (b'rtl_logo', 102),
            (b'sailboat', 104),
            (b'sb_down_arrow', 106),
            (b'sb_h_double_arrow', 108),
            (b'sb_left_arrow', 110),
            (b'sb_right_arrow', 112),
            (b'sb_up_arrow', 114),
            (b'sb_v_double_arrow', 116),
            (b'shuttle', 118),
            (b'sizing', 120),
            (b'spider', 122),
            (b'spraycan', 124),
            (b'star', 126),
            (b'target', 128),
            (b'tcross', 130),
            (b'top_left_arrow', 132),
            (b'top_left_corner', 134),
            (b'top_right_corner', 136),
            (b'top_side', 138),
            (b'top_tee', 140),
            (b'trek', 142),
            (b'ul_angle', 144),
            (b'umbrella', 146),
            (b'ur_angle', 148),
            (b'watch', 150),
            (b'xterm', 152)
        )

        self.xcursor = self._setup_xcursor_binding()

        for name, cursor_font in cursors:
            self._new(name, cursor_font)

        if self.xcursor:
            self.xcursor.xcb_cursor_context_free(self._cursor_ctx[0])

    def finalize(self):
        self._cursor_ctx = None

    def _setup_xcursor_binding(self):
        try:
            xcursor = ffi.dlopen('libxcb-cursor.so')
        except OSError:
            self.log.warning("xcb-cursor not found, fallback to font pointer")
            return False

        conn = self.conn.conn
        screen_pointer = conn.get_screen_pointers()[0]
        self._cursor_ctx = ffi.new('xcb_cursor_context_t **')
        xcursor.xcb_cursor_context_new(conn._conn, screen_pointer,
                                       self._cursor_ctx)

        return xcursor

    def get_xcursor(self, name):
        """
        Get the cursor using xcb-util-cursor, so we support themed cursors
        """
        cursor = self.xcursor.xcb_cursor_load_cursor(self._cursor_ctx[0], name)
        return cursor

    def get_font_cursor(self, name, cursor_font):
        """
        Get the cursor from the font, used as a fallback if xcb-util-cursor
        is not installed
        """
        fid = self.conn.conn.generate_id()
        self.conn.conn.core.OpenFont(fid, len("cursor"), "cursor")
        cursor = self.conn.conn.generate_id()
        self.conn.conn.core.CreateGlyphCursor(
            cursor, fid, fid,
            cursor_font, cursor_font + 1,
            0, 0, 0,
            65535, 65535, 65535
        )
        return cursor

    def _new(self, name, cursor_font):
        if self.xcursor:
            cursor = self.get_xcursor(name)
        else:
            cursor = self.get_font_cursor(name, cursor_font)
        self[name.decode()] = cursor
