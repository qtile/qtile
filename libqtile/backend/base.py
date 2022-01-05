from __future__ import annotations

import contextlib
import enum
import math
import typing
from abc import ABCMeta, abstractmethod

import cairocffi

from libqtile import drawer, pangocffi, utils
from libqtile.command.base import CommandError, CommandObject
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Any

    from libqtile import config
    from libqtile.command.base import ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.utils import ColorsType


class Core(CommandObject, metaclass=ABCMeta):
    painter: Any
    supports_restarting: bool = True

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

    def update_desktops(self, groups: list[_Group], index: int) -> None:
        """Set the current desktops of the window manager"""

    @abstractmethod
    def get_screen_info(self) -> list[tuple[int, int, int, int]]:
        """Get the screen information"""

    @abstractmethod
    def grab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Configure the backend to grab the key event"""

    @abstractmethod
    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
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

    def distribute_windows(self, initial: bool) -> None:
        """Distribute windows to groups. `initial` will be `True` if Qtile just started."""

    def warp_pointer(self, x: int, y: int) -> None:
        """Warp the pointer to the given coordinates relative."""

    def update_client_list(self, windows_map: dict[int, WindowType]) -> None:
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

    def simulate_keypress(self, modifiers: list[str], key: str) -> None:
        """Simulate a keypress with given modifiers"""

    def keysym_from_name(self, name: str) -> int:
        """Get the keysym for a key from its name"""
        raise NotImplementedError

    def cmd_info(self) -> dict:
        """Get basic information about the running backend."""
        return {"backend": self.name, "display_name": self.display_name}


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
        self.reserved_space: tuple[int, int, int, int] | None = None
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

    def get_wm_class(self) -> list | None:
        """Return the class(es) of the window"""
        return None

    def get_wm_type(self) -> str | None:
        """Return the type of the window"""
        return None

    def get_wm_role(self) -> str | None:
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

    @property
    def opacity(self) -> float:
        """The opacity of this window from 0 (transparent) to 1 (opaque)."""
        return self._opacity

    @opacity.setter
    def opacity(self, opacity: float) -> None:
        """Opacity setter."""
        self._opacity = opacity

    @abstractmethod
    def place(
        self,
        x,
        y,
        width,
        height,
        borderwidth,
        bordercolor,
        above=False,
        margin=None,
        respect_hints=False,
    ):
        """Place the window in the given position."""

    def _items(self, name: str) -> ItemT:
        return None

    def _select(self, name, sel):
        return None

    @abstractmethod
    def info(self) -> dict[str, Any]:
        """
        Return information on this window.

        Mimimum required keys are:
        - name
        - x
        - y
        - width
        - height
        - group
        - id
        - wm_class

        """
        return {}

    def cmd_info(self) -> dict:
        """Return a dictionary of info."""
        return self.info()


class Window(_Window, metaclass=ABCMeta):
    """
    A regular Window belonging to a client.

    Abstract methods are required to be defined as part of a specific backend's
    implementation. Non-abstract methods have default implementations here to be shared
    across backends.
    """

    qtile: Qtile

    # If float_x or float_y are None, the window has never floated
    float_x: int | None
    float_y: int | None

    def __repr__(self):
        return "Window(name=%r, wid=%i)" % (self.name, self.wid)

    @property
    @abstractmethod
    def group(self) -> _Group | None:
        """The group to which this window belongs."""

    @property
    def floating(self) -> bool:
        """Whether this window is floating."""
        return False

    @floating.setter
    def floating(self, do_float: bool) -> None:
        raise NotImplementedError

    @property
    def maximized(self) -> bool:
        """Whether this window is maximized."""
        return False

    @maximized.setter
    def maximized(self, do_maximize: bool) -> None:
        raise NotImplementedError

    @property
    def minimized(self) -> bool:
        """Whether this window is minimized."""
        return False

    @minimized.setter
    def minimized(self, do_minimize: bool) -> None:
        raise NotImplementedError

    @property
    def fullscreen(self) -> bool:
        """Whether this window is fullscreened."""
        return False

    @fullscreen.setter
    def fullscreen(self, do_full: bool) -> None:
        raise NotImplementedError

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
        self, group_name: str | None = None, *, switch_group: bool = False, toggle: bool = False
    ) -> None:
        """Move window to a specified group

        Also switch to that group if switch_group is True.

        If `toggle` is True and and the specified group is already on the screen,
        use the last used group as target instead.
        """

    @property
    def has_focus(self):
        return self == self.qtile.current_window

    def has_user_set_position(self) -> bool:
        """Whether this window has user-defined geometry"""
        return False

    def is_transient_for(self) -> WindowType | None:
        """What window is this window a transient window for?"""
        return None

    @abstractmethod
    def get_pid(self) -> int:
        """Return the PID that owns the window."""

    def paint_borders(self, color: ColorsType, width: int) -> None:
        """Paint the window borders with the given color(s) and width"""

    @abstractmethod
    def cmd_focus(self, warp: bool = True) -> None:
        """Focuses the window."""

    def cmd_match(self, *args, **kwargs) -> bool:
        return self.match(*args, **kwargs)

    @abstractmethod
    def cmd_get_position(self) -> tuple[int, int]:
        """Get the (x, y) of the window"""

    @abstractmethod
    def cmd_get_size(self) -> tuple[int, int]:
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
    def cmd_set_position(self, x: int, y: int) -> None:
        """
        Move floating window to x and y; swap tiling window with the window under the
        pointer.
        """

    @abstractmethod
    def cmd_set_size_floating(self, w: int, h: int) -> None:
        """Set window dimensions to w and h"""

    @abstractmethod
    def cmd_place(
        self, x, y, width, height, borderwidth, bordercolor, above=False, margin=None
    ) -> None:
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
        """Toggle the maximize state of the window."""

    @abstractmethod
    def cmd_toggle_minimize(self) -> None:
        """Toggle the minimize state of the window."""

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
        self,
        group_name: str | None = None,
        groupName: str | None = None,  # Deprecated  # noqa: N803
        switch_group: bool = False,
        toggle: bool = False,
    ) -> None:
        """Move window to a specified group

        Also switch to that group if `switch_group` is True.

        If `toggle` is True and and the specified group is already on the screen,
        use the last used group as target instead.

        `groupName` is deprecated and will be dropped soon. Please use `group_name`
        instead.
        """
        if groupName is not None:
            logger.warning("Window.cmd_togroup's groupName is deprecated; use group_name")
            group_name = groupName
        self.togroup(group_name, switch_group=switch_group, toggle=toggle)

    def cmd_toscreen(self, index: int | None = None) -> None:
        """Move window to a specified screen.

        If index is not specified, we assume the current screen

        Examples
        ========

        Move window to current screen::

            toscreen()

        Move window to screen 0::

            toscreen(0)
        """
        if index is None:
            screen = self.qtile.current_screen
        else:
            try:
                screen = self.qtile.screens[index]
            except IndexError:
                raise CommandError("No such screen: %d" % index)
        self.togroup(screen.group.name)

    def cmd_opacity(self, opacity: float) -> None:
        """Set the window's opacity.

        The value must be between 0 and 1 inclusive.
        """
        if opacity < 0.1:
            self.opacity = 0.1
        elif opacity > 1:
            self.opacity = 1
        else:
            self.opacity = opacity

    def cmd_down_opacity(self) -> None:
        """Decrease the window's opacity by 10%."""
        if self.opacity > 0.2:
            # don't go completely clear
            self.opacity -= 0.1
        else:
            self.opacity = 0.1

    def cmd_up_opacity(self) -> None:
        """Increase the window's opacity by 10%."""
        if self.opacity < 0.9:
            self.opacity += 0.1
        else:
            self.opacity = 1

    @abstractmethod
    def cmd_kill(self) -> None:
        """Kill the window. Try to be polite."""

    @abstractmethod
    def cmd_static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Makes this window a static window, attached to a Screen.

        Values left unspecified are taken from the existing window state.
        """
        self.defunct = True

    def cmd_center(self) -> None:
        """Centers a floating window on the screen."""
        if not self.floating:
            return

        if not (self.group and self.group.screen):
            return

        screen = self.group.screen

        x = (screen.width - self.width) // 2  # type: ignore
        y = (screen.height - self.height) // 2  # type: ignore

        self.place(
            x,
            y,
            self.width,  # type: ignore
            self.height,  # type: ignore
            self.borderwidth,
            self.bordercolor,  # type: ignore
            above=True,
            respect_hints=True,
        )


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

    def info(self) -> dict:
        """Return a dictionary of info."""
        return dict(
            name=self.name,
            wm_class=self.get_wm_class(),
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            id=self.wid,
        )

    @abstractmethod
    def cmd_bring_to_front(self) -> None:
        """Bring the window to the front"""


WindowType = typing.Union[Window, Internal, Static]


class Drawer:
    """A helper class for drawing to Internal windows.

    We stage drawing operations locally in memory using a cairo RecordingSurface before
    finally drawing all operations to a backend-specific target.
    """

    # We need to track extent of drawing to know when to redraw.
    previous_rect: tuple[int, int, int | None, int | None]
    current_rect: tuple[int, int, int | None, int | None]

    def __init__(self, qtile: Qtile, win: Internal, width: int, height: int):
        self.qtile = qtile
        self._win = win
        self._width = width
        self._height = height

        self.surface: cairocffi.RecordingSurface
        self.ctx: cairocffi.Context
        self._reset_surface()

        self.mirrors: dict[Drawer, bool] = {}

        self.current_rect = (0, 0, 0, 0)
        self.previous_rect = (-1, -1, -1, -1)
        self._enabled = True

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

    def _check_surface_reset(self):
        """
        Checks to see if the widget is not being reflected and
        then clears RecordingSurface of operations.
        """
        if not self.mirrors:
            self._reset_surface()

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
        self.ctx.arc(x + width - delta, y + delta, radius, -90 * degrees, 0 * degrees)
        self.ctx.arc(x + width - delta, y + height - delta, radius, 0 * degrees, 90 * degrees)
        self.ctx.arc(x + delta, y + height - delta, radius, 90 * degrees, 180 * degrees)
        self.ctx.arc(x + delta, y + delta, radius, 180 * degrees, 270 * degrees)
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

    def enable(self):
        """Enable drawing of surface to Internal window."""
        self._enabled = True

    def disable(self):
        """Disable drawing of surface to Internal window."""
        self._enabled = False

    def draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
    ):
        """
        A wrapper for the draw operation.

        This draws our cached operations to the Internal window.

        If Drawer has been disabled then the RecordingSurface will
        be cleared if no mirrors are waiting to copy its contents.

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
        if self._enabled:
            self._draw(offsetx, offsety, width, height)

        # Check to see if RecordingSurface can be cleared.
        self._check_surface_reset()

    def _draw(
        self,
        offsetx: int = 0,
        offsety: int = 0,
        width: int | None = None,
        height: int | None = None,
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

    def set_source_rgb(self, colour: ColorsType, ctx: cairocffi.Context | None = None):
        # If an alternate context is not provided then we draw to the
        # drawer's default context
        if ctx is None:
            ctx = self.ctx
        if isinstance(colour, list):
            if len(colour) == 0:
                # defaults to black
                ctx.set_source_rgba(0.0, 0.0, 0.0, 1.0)
            elif len(colour) == 1:
                ctx.set_source_rgba(*utils.rgb(colour[0]))
            else:
                linear = cairocffi.LinearGradient(0.0, 0.0, 0.0, self.height)
                step_size = 1.0 / (len(colour) - 1)
                step = 0.0
                for c in colour:
                    linear.add_color_stop_rgba(step, *utils.rgb(c))
                    step += step_size
                ctx.set_source(linear)
        else:
            ctx.set_source_rgba(*utils.rgb(colour))

    def clear(self, colour):
        self.set_source_rgb(colour)
        self.ctx.rectangle(0, 0, self.width, self.height)
        self.ctx.fill()

    def textlayout(self, text, colour, font_family, font_size, font_shadow, markup=False, **kw):
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
        self.ctx.set_font_size(int(heightlimit * heightlimit / height))
        return self.font_extents()

    def fit_text(self, strings, heightlimit):
        """Try to find a maximum font size that fits all strings within the height"""
        self.ctx.set_font_size(heightlimit)
        _, _, _, maxheight, _, _ = self.ctx.text_extents("".join(strings))
        if not maxheight:
            return 0, 0
        self.ctx.set_font_size(int(heightlimit * heightlimit / maxheight))
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
