from __future__ import annotations

import contextlib
import enum
import math
import typing
from abc import ABCMeta, abstractmethod

import cairocffi

from libqtile import drawer, pangocffi, utils
from libqtile.command.base import CommandObject

if typing.TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Tuple, Union

    from libqtile import config
    from libqtile.command.base import ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.utils import ColorType


class Core(CommandObject, metaclass=ABCMeta):
    painter: Any

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the backend"""
        pass

    def _items(self, name: str) -> ItemT:
        return None

    def _select(self, name, sel):
        return None

    @abstractmethod
    def finalize(self):
        """Destructor/Clean up resources"""

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    def setup_listener(self, qtile: Qtile) -> None:
        """Setup a listener for the given qtile instance"""

    @abstractmethod
    def remove_listener(self) -> None:
        """Setup a listener for the given qtile instance"""

    def update_desktops(self, groups: List[_Group], index: int) -> None:
        """Set the current desktops of the window manager"""

    @abstractmethod
    def get_screen_info(self) -> List[Tuple[int, int, int, int]]:
        """Get the screen information"""

    @abstractmethod
    def grab_key(self, key: Union[config.Key, config.KeyChord]) -> Tuple[int, int]:
        """Configure the backend to grab the key event"""

    @abstractmethod
    def ungrab_key(self, key: Union[config.Key, config.KeyChord]) -> Tuple[int, int]:
        """Release the given key event"""

    @abstractmethod
    def ungrab_keys(self) -> None:
        """Release the grabbed key events"""

    @abstractmethod
    def grab_button(self, mouse: config.Mouse) -> int:
        """Configure the backend to grab the mouse event"""

    @abstractmethod
    def ungrab_buttons(self) -> None:
        """Release the grabbed button events"""

    @abstractmethod
    def grab_pointer(self) -> None:
        """Configure the backend to grab mouse events"""

    @abstractmethod
    def ungrab_pointer(self) -> None:
        """Release grabbed pointer events"""

    def scan(self) -> None:
        """Scan for clients if required."""

    def warp_pointer(self, x: int, y: int) -> None:
        """Warp the pointer to the given coordinates relative."""

    def update_client_list(self, windows_map: Dict[int, WindowType]) -> None:
        """Update the list of windows being managed"""

    @contextlib.contextmanager
    def masked(self):
        """A context manager to suppress window events while operating on many windows."""
        yield

    def create_internal(self, x: int, y: int, width: int, height: int) -> Internal:
        """Create an internal window controlled by Qtile."""
        raise NotImplementedError  # Only error when called, not when instantiating class

    def flush(self) -> None:
        """If needed, flush the backend's event queue."""

    def graceful_shutdown(self):
        """Try to close windows gracefully before exiting"""

    def simulate_keypress(self, modifiers: List[str], key: str) -> None:
        """Simulate a keypress with given modifiers"""

    def keysym_from_name(self, name: str) -> int:
        """Get the keysym for a key from its name"""
        raise NotImplementedError

    def change_vt(self, vt: int) -> bool:
        """Change virtual terminal, returning success."""
        return False

    def cmd_info(self):
        return {
            "backend": self.name,
            "display_name": self.display_name
        }


@enum.unique
class FloatStates(enum.Enum):
    NOT_FLOATING = 1
    FLOATING = 2
    MAXIMIZED = 3
    FULLSCREEN = 4
    TOP = 5
    MINIMIZED = 6


class _Window(CommandObject, metaclass=ABCMeta):
    def __init__(self):
        self.borderwidth: int = 0
        self.name: str = "<no name>"
        self.reserved_space: Optional[Tuple[int, int, int, int]] = None
        # Window.cmd_static sets this in case it is hooked to client_new to stop the
        # Window object from being managed, now that a Static is being used instead
        self.defunct: bool = False

    @property
    @abstractmethod
    def wid(self) -> int:
        """The unique window ID"""

    @abstractmethod
    def hide(self) -> None:
        """Hide the window"""

    @abstractmethod
    def unhide(self) -> None:
        """Unhide the window"""

    @abstractmethod
    def kill(self) -> None:
        """Kill the window"""

    def get_wm_class(self) -> Optional[List]:
        """Return the class(es) of the window"""
        return None

    def get_wm_type(self) -> Optional[str]:
        """Return the type of the window"""
        return None

    def get_wm_role(self) -> Optional[str]:
        """Return the role of the window"""
        return None

    @property
    def can_steal_focus(self):
        """Is it OK for this window to steal focus?"""
        return True

    def has_fixed_ratio(self) -> bool:
        """Does this window want a fixed aspect ratio?"""
        return False

    def has_fixed_size(self) -> bool:
        """Does this window want a fixed size?"""
        return False

    @property
    def urgent(self):
        """Whether this window urgently wants focus"""
        return False

    @abstractmethod
    def place(self, x, y, width, height, borderwidth, bordercolor,
              above=False, margin=None, respect_hints=False):
        """Place the window in the given position."""

    def _items(self, name: str) -> ItemT:
        return None

    def _select(self, name, sel):
        return None

    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Return information on this window."""
        return {}

    def cmd_info(self) -> Dict:
        """Return a dictionary of info."""
        return self.info()


class Window(_Window, metaclass=ABCMeta):
    """A regular Window belonging to a client."""

    # If float_x or float_y are None, the window has never floated
    float_x: Optional[int]
    float_y: Optional[int]

    def __repr__(self):
        return "Window(name=%r, wid=%i)" % (self.name, self.wid)

    @property
    @abstractmethod
    def group(self) -> Optional[_Group]:
        """The group to which this window belongs."""

    @property
    def floating(self) -> bool:
        """Whether this window is floating."""
        return False

    @property
    def maximized(self) -> bool:
        """Whether this window is maximized."""
        return False

    @property
    def fullscreen(self) -> bool:
        """Whether this window is fullscreened."""
        return False

    @property
    def wants_to_fullscreen(self) -> bool:
        """Does this window want to be fullscreen?"""
        return False

    def match(self, match: config.Match) -> bool:
        """Compare this window against a Match instance."""
        return match.compare(self)

    @abstractmethod
    def focus(self, warp: bool) -> None:
        """Focus this window and optional warp the pointer to it."""

    @abstractmethod
    def togroup(
        self, group_name: Optional[str] = None, *, switch_group: bool = False
    ) -> None:
        """Move window to a specified group

        Also switch to that group if switch_group is True.
        """

    @property
    def has_focus(self):
        return self == self.qtile.current_window

    def has_user_set_position(self) -> bool:
        """Whether this window has user-defined geometry"""
        return False

    def is_transient_for(self) -> Optional["WindowType"]:
        """What window is this window a transient window for?"""
        return None

    @abstractmethod
    def get_pid(self) -> int:
        """Return the PID that owns the window."""

    def paint_borders(self, color: Union[ColorType, List[ColorType]], width: int) -> None:
        """Paint the window borders with the given color(s) and width"""

    @abstractmethod
    def cmd_focus(self, warp: bool = True) -> None:
        """Focuses the window."""

    @abstractmethod
    def cmd_get_position(self) -> Tuple[int, int]:
        """Get the (x, y) of the window"""

    @abstractmethod
    def cmd_get_size(self) -> Tuple[int, int]:
        """Get the (width, height) of the window"""

    @abstractmethod
    def cmd_move_floating(self, dx: int, dy: int) -> None:
        """Move window by dx and dy"""

    @abstractmethod
    def cmd_resize_floating(self, dw: int, dh: int) -> None:
        """Add dw and dh to size of window"""

    @abstractmethod
    def cmd_set_position_floating(self, x: int, y: int) -> None:
        """Move window to x and y"""

    @abstractmethod
    def cmd_set_size_floating(self, w: int, h: int) -> None:
        """Set window dimensions to w and h"""

    @abstractmethod
    def cmd_place(self, x, y, width, height, borderwidth, bordercolor,
                  above=False, margin=None) -> None:
        """Place the window with the given position and geometry."""

    @abstractmethod
    def cmd_toggle_floating(self) -> None:
        """Toggle the floating state of the window."""

    @abstractmethod
    def cmd_enable_floating(self) -> None:
        """Float the window."""

    @abstractmethod
    def cmd_disable_floating(self) -> None:
        """Tile the window."""

    @abstractmethod
    def cmd_toggle_maximize(self) -> None:
        """Toggle the fullscreen state of the window."""

    @abstractmethod
    def cmd_toggle_fullscreen(self) -> None:
        """Toggle the fullscreen state of the window."""

    @abstractmethod
    def cmd_enable_fullscreen(self) -> None:
        """Fullscreen the window"""

    @abstractmethod
    def cmd_disable_fullscreen(self) -> None:
        """Un-fullscreen the window"""

    @abstractmethod
    def cmd_bring_to_front(self) -> None:
        """Bring the window to the front"""

    def cmd_togroup(
        self, group_name: Optional[str] = None, *, switch_group: bool = False
    ) -> None:
        """Move window to a specified group

        Also switch to that group if switch_group is True.
        """
        self.togroup(group_name, switch_group=switch_group)

    def cmd_opacity(self, opacity):
        """Set the window's opacity"""
        if opacity < .1:
            self.opacity = .1
        elif opacity > 1:
            self.opacity = 1
        else:
            self.opacity = opacity

    def cmd_down_opacity(self):
        """Decrease the window's opacity"""
        if self.opacity > .2:
            # don't go completely clear
            self.opacity -= .1
        else:
            self.opacity = .1

    def cmd_up_opacity(self):
        """Increase the window's opacity"""
        if self.opacity < .9:
            self.opacity += .1
        else:
            self.opacity = 1

    @abstractmethod
    def cmd_kill(self) -> None:
        """Kill the window. Try to be polite."""

    @abstractmethod
    def cmd_static(
        self,
        screen: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        """Makes this window a static window, attached to a Screen.

        Values left unspecified are taken from the existing window state.
        """
        self.defunct = True


class Internal(_Window, metaclass=ABCMeta):
    """An Internal window belonging to Qtile."""
    def __repr__(self):
        return "Internal(wid=%s)" % self.wid

    @abstractmethod
    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""

    def process_window_expose(self) -> None:
        """Respond to the window being exposed. Required by X11 backend."""

    def process_button_click(self, x: int, y: int, button: int) -> None:
        """Handle a pointer button click."""

    def process_button_release(self, x: int, y: int, button: int) -> None:
        """Handle a pointer button release."""

    def process_pointer_enter(self, x: int, y: int) -> None:
        """Handle the pointer entering the window."""

    def process_pointer_leave(self, x: int, y: int) -> None:
        """Handle the pointer leaving the window."""

    def process_pointer_motion(self, x: int, y: int) -> None:
        """Handle pointer motion within the window."""

    def process_key_press(self, keycode: int) -> None:
        """Handle a key press."""


class Static(_Window, metaclass=ABCMeta):
    """A window bound to a screen rather than a group."""
    screen: config.Screen
    x: Any
    y: Any
    width: Any
    height: Any

    def __repr__(self):
        return "Static(name=%r, wid=%s)" % (self.name, self.wid)

    def info(self) -> Dict:
        """Return a dictionary of info."""
        return dict(
            name=self.name,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            id=self.wid,
        )


WindowType = typing.Union[Window, Internal, Static]


class Drawer:
    """A helper class for drawing to Internal windows.

    We stage drawing operations locally in memory using a cairo RecordingSurface before
    finally drawing all operations to a backend-specific target.
    """
    # We need to track extent of drawing to know when to redraw.
    previous_rect: Tuple[int, int, Optional[int], Optional[int]]
    current_rect: Tuple[int, int, Optional[int], Optional[int]]

    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        self.qtile = qtile
        self._win = win
        self._width = width
        self._height = height

        self.surface: cairocffi.RecordingSurface
        self.ctx: cairocffi.Context
        self._reset_surface()

        self.mirrors: Dict[Drawer, bool] = {}

        self.current_rect = (0, 0, 0, 0)
        self.previous_rect = (-1, -1, -1, -1)

    def finalize(self):
        """Destructor/Clean up resources"""
        self.surface = None
        self.ctx = None

    def add_mirror(self, mirror: Drawer):
        """Keep details of other drawers that are mirroring this one."""
        self.mirrors[mirror] = False

    def reset_mirrors(self):
        """Reset the drawn status of mirrors."""
        self.mirrors = {m: False for m in self.mirrors}

    @property
    def mirrors_drawn(self) -> bool:
        """Returns True if all mirrors have been drawn with the current surface."""
        return all(v for v in self.mirrors.values())

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, width: int):
        self._width = width

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, height: int):
        self._height = height

    def _reset_surface(self):
        """This creates a fresh surface and cairo context."""
        self.surface = cairocffi.RecordingSurface(
            cairocffi.CONTENT_COLOR_ALPHA,
            None,
        )
        self.ctx = self.new_ctx()

    @property
    def needs_update(self) -> bool:
        # We can't test for the surface's ink_extents here on its own as a completely
        # transparent background would not show any extents but we may still need to
        # redraw (e.g. if a Spacer widget has changed position and/or size)
        # Check if the size of the area being drawn has changed
        rect_changed = self.current_rect != self.previous_rect

        # Check if draw has content (would be False for completely transparent drawer)
        ink_changed = any(not math.isclose(0.0, i) for i in self.surface.ink_extents())

        return ink_changed or rect_changed

    def paint_to(self, drawer: Drawer) -> None:
        drawer.ctx.set_source_surface(self.surface)
        drawer.ctx.paint()
        self.mirrors[drawer] = True

        if self.mirrors_drawn:
            self._reset_surface()
            self.reset_mirrors()

    def _rounded_rect(self, x, y, width, height, linewidth):
        aspect = 1.0
        corner_radius = height / 10.0
        radius = corner_radius / aspect
        degrees = math.pi / 180.0

        self.ctx.new_sub_path()

        delta = radius + linewidth / 2
        self.ctx.arc(x + width - delta, y + delta, radius,
                     -90 * degrees, 0 * degrees)
        self.ctx.arc(x + width - delta, y + height - delta,
                     radius, 0 * degrees, 90 * degrees)
        self.ctx.arc(x + delta, y + height - delta, radius,
                     90 * degrees, 180 * degrees)
        self.ctx.arc(x + delta, y + delta, radius,
                     180 * degrees, 270 * degrees)
        self.ctx.close_path()

    def rounded_rectangle(self, x: int, y: int, width: int, height: int, linewidth: int):
        self._rounded_rect(x, y, width, height, linewidth)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()

    def rounded_fillrect(self, x: int, y: int, width: int, height: int, linewidth: int):
        self._rounded_rect(x, y, width, height, linewidth)
        self.ctx.fill()

    def rectangle(self, x: int, y: int, width: int, height: int, linewidth: int = 2):
        self.ctx.set_line_width(linewidth)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.stroke()

    def fillrect(self, x: int, y: int, width: int, height: int, linewidth: int = 2):
        self.ctx.set_line_width(linewidth)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.fill()
        self.ctx.stroke()

    def draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        """
        This draws our cached operations to the Internal window.

        Parameters
        ==========

        offsetx :
            the X offset to start drawing at.
        offsety :
            the Y offset to start drawing at.
        width :
            the X portion of the canvas to draw at the starting point.
        height :
            the Y portion of the canvas to draw at the starting point.
        """

    def new_ctx(self):
        return pangocffi.patch_cairo_context(cairocffi.Context(self.surface))

    def set_source_rgb(self, colour: Union[ColorType, List[ColorType]], ctx: cairocffi.Context = None):
        # If an alternate context is not provided then we draw to the
        # drawer's default context
        if ctx is None:
            ctx = self.ctx
        if isinstance(colour, list):
            if len(colour) == 0:
                # defaults to black
                ctx.set_source_rgba(*utils.rgb("#000000"))
            elif len(colour) == 1:
                ctx.set_source_rgba(*utils.rgb(colour[0]))
            else:
                linear = cairocffi.LinearGradient(0.0, 0.0, 0.0, self.height)
                step_size = 1.0 / (len(colour) - 1)
                step = 0.0
                for c in colour:
                    rgb_col = utils.rgb(c)
                    if len(rgb_col) < 4:
                        rgb_col[3] = 1
                    linear.add_color_stop_rgba(step, *rgb_col)
                    step += step_size
                ctx.set_source(linear)
        else:
            ctx.set_source_rgba(*utils.rgb(colour))

    def clear(self, colour):
        self.set_source_rgb(colour)
        self.ctx.rectangle(0, 0, self.width, self.height)
        self.ctx.fill()

    def textlayout(
        self, text, colour, font_family, font_size, font_shadow, markup=False, **kw
    ):
        """Get a text layout"""
        textlayout = drawer.TextLayout(
            self, text, colour, font_family, font_size, font_shadow, markup=markup, **kw
        )
        return textlayout

    def max_layout_size(self, texts, font_family, font_size):
        sizelayout = self.textlayout("", "ffffff", font_family, font_size, None)
        widths, heights = [], []
        for i in texts:
            sizelayout.text = i
            widths.append(sizelayout.width)
            heights.append(sizelayout.height)
        return max(widths), max(heights)

    def text_extents(self, text):
        return self.ctx.text_extents(utils.scrub_to_utf8(text))

    def font_extents(self):
        return self.ctx.font_extents()

    def fit_fontsize(self, heightlimit):
        """Try to find a maximum font size that fits any strings within the height"""
        self.ctx.set_font_size(heightlimit)
        asc, desc, height, _, _ = self.font_extents()
        self.ctx.set_font_size(
            int(heightlimit * heightlimit / height))
        return self.font_extents()

    def fit_text(self, strings, heightlimit):
        """Try to find a maximum font size that fits all strings within the height"""
        self.ctx.set_font_size(heightlimit)
        _, _, _, maxheight, _, _ = self.ctx.text_extents("".join(strings))
        if not maxheight:
            return 0, 0
        self.ctx.set_font_size(
            int(heightlimit * heightlimit / maxheight))
        maxwidth, maxheight = 0, 0
        for i in strings:
            _, _, x, y, _, _ = self.ctx.text_extents(i)
            maxwidth = max(maxwidth, x)
            maxheight = max(maxheight, y)
        return maxwidth, maxheight

    def draw_vbar(self, color, x, y1, y2, linewidth=1):
        self.set_source_rgb(color)
        self.ctx.move_to(x, y1)
        self.ctx.line_to(x, y2)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()

    def draw_hbar(self, color, x1, x2, y, linewidth=1):
        self.set_source_rgb(color)
        self.ctx.move_to(x1, y)
        self.ctx.line_to(x2, y)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()
