# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

from __future__ import annotations

import typing
from collections import defaultdict

from libqtile import configurable, hook
from libqtile.command.base import CommandObject, expose_command
from libqtile.log_utils import logger
from libqtile.utils import has_transparency, is_valid_colors

if typing.TYPE_CHECKING:
    import asyncio
    from typing import Any

    from libqtile.backend.base import Drawer, Internal, WindowType
    from libqtile.command.base import ItemT
    from libqtile.config import Screen
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType
    from libqtile.widget.base import _Widget

NESW = ("top", "right", "bottom", "left")


class Gap:
    """A gap placed along one of the edges of the screen

    Qtile will avoid covering gaps with windows.

    Parameters
    ==========
    size :
        The "thickness" of the gap, i.e. the height of a horizontal gap, or the
        width of a vertical gap.
    """

    def __init__(self, size: int) -> None:
        self.length: int = 0  # width of a horizontal gap or the height of a vertical gap
        self.size: int = size  # height of a horizontal gap or the width of a vertical gap
        self.fullsize: int = size  # sum of 'size' and margins
        self.qtile: Qtile | None = None
        self.screen: Screen | None = None
        self.x: int = 0
        self.y: int = 0
        self.width: int = 0
        self.height: int = 0
        self.horizontal: bool = False

        # Additional reserved around the gap/bar, used when space is dynamically
        # reserved e.g. by third-party bars.
        self.margin: list[int] = [0, 0, 0, 0]  # [N, E, S, W]

    def _configure(self, qtile: Qtile, screen: Screen, reconfigure: bool = False) -> None:
        self.qtile = qtile
        self.screen = screen
        self.fullsize = self.size
        # If both horizontal and vertical gaps are present, screen corners are
        # given to the horizontal ones
        if screen.top is self:
            self.x = screen.x + self.margin[3]
            self.y = screen.y + self.margin[0]
            self.length = screen.width - self.margin[1] - self.margin[3]
            self.width = self.length
            self.height = self.size
            self.horizontal = True
            self.fullsize += self.margin[0] + self.margin[2]
        elif screen.bottom is self:
            self.x = screen.x + self.margin[3]
            self.y = screen.dy + screen.dheight - self.margin[2]
            self.length = screen.width - self.margin[1] - self.margin[3]
            self.width = self.length
            self.height = self.size
            self.horizontal = True
            self.fullsize += self.margin[0] + self.margin[2]
        elif screen.left is self:
            self.x = screen.x + self.margin[3]
            self.y = screen.dy + self.margin[0]
            self.length = screen.dheight - self.margin[0] - self.margin[2]
            self.width = self.size
            self.height = self.length
            self.horizontal = False
            self.fullsize += self.margin[1] + self.margin[3]
        else:  # right
            self.x = screen.dx + screen.dwidth - self.margin[1]
            self.y = screen.dy + self.margin[0]
            self.length = screen.dheight - self.margin[0] - self.margin[2]
            self.width = self.size
            self.height = self.length
            self.horizontal = False
            self.fullsize += self.margin[1] + self.margin[3]

    def draw(self) -> None:
        pass

    def finalize(self) -> None:
        pass

    def geometry(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)

    @property
    def position(self) -> str:
        for i in NESW:
            if getattr(self.screen, i) is self:
                return i
        assert False, "Not reached"

    def adjust_reserved_space(self, size: int) -> None:
        for i, side in enumerate(NESW):
            if getattr(self.screen, side) is self:
                self.margin[i] += size
            if self.margin[i] < 0:
                raise ValueError("Gap/Bar can't reserve negative space.")

    @expose_command()
    def info(self) -> dict[str, Any]:
        """
        Info for this object.
        """
        return dict(position=self.position)


class Obj:
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name


STRETCH = Obj("STRETCH")
CALCULATED = Obj("CALCULATED")
STATIC = Obj("STATIC")


class Bar(Gap, configurable.Configurable, CommandObject):
    """A bar, which can contain widgets

    Parameters
    ==========
    widgets :
        A list of widget objects.
    size :
        The "thickness" of the bar, i.e. the height of a horizontal bar, or the
        width of a vertical bar.
    """

    defaults = [
        ("background", "#000000", "Background colour."),
        ("opacity", 1, "Bar window opacity."),
        ("margin", 0, "Space around bar as int or list of ints [N E S W]."),
        ("border_color", "#000000", "Border colour as str or list of str [N E S W]"),
        ("border_width", 0, "Width of border as int of list of ints [N E S W]"),
        (
            "reserve",
            True,
            "Reserve screen space (when set to 'False', bar will be drawn above windows).",
        ),
    ]

    def __init__(self, widgets: list[_Widget], size: int, **config: Any) -> None:
        Gap.__init__(self, size)
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Bar.defaults)
        # We need to create a new widget list here as users may have the same list for multiple
        # screens. In that scenario, if we replace the widget with a mirror, it replaces it in every
        # bar as python is referring to the same list.
        self.widgets = widgets.copy()
        self.window: Internal | None = None
        self.drawer: Drawer
        self._configured = False
        self._draw_queued = False
        self.future: asyncio.Handle | None = None

        # The part of the margins that was reserved by clients
        self._reserved_space: list[int] = [0, 0, 0, 0]  # [N, E, S, W]
        self._reserved_space_updated = False

        # Size saved when hiding the bar
        self._saved_size = 0

        # Previous window when the bar grabs the keyboard
        self._saved_focus: WindowType | None = None

        # Track widgets that are receiving input
        self._has_cursor: _Widget | None = None
        self._has_keyboard: _Widget | None = None

        # Because Gap.__init__ also sets self.margin
        self.margin = config.get("margin", self.margin)

        # Hacky solution that shows limitations of typing Configurable. We want the
        # option to accept `int | list[int]` but the attribute to be `list[int]`.
        self.margin: list[int]
        if isinstance(self.margin, int):  # type: ignore [unreachable]
            self.margin = [self.margin] * 4  # type: ignore [unreachable]

        self.border_width: list[int]
        if isinstance(self.border_width, int):  # type: ignore [unreachable]
            self.border_width = [self.border_width] * 4  # type: ignore [unreachable]

        self.border_color: ColorsType

        # Check if colours are valid but don't convert to rgba here
        if is_valid_colors(self.border_color):
            if not isinstance(self.border_color, list):
                self.border_color = [self.border_color] * 4
        else:
            logger.warning("Invalid border_color specified. Borders will not be displayed.")
            self.border_width = [0, 0, 0, 0]

    def _configure(self, qtile: Qtile, screen: Screen, reconfigure: bool = False) -> None:
        """
        Configure the bar. `reconfigure` is set to True when screen dimensions
        change, forcing a recalculation of the bar's dimensions.
        """
        # We only want to adjust margin sizes once unless there's new space being
        # reserved or we're reconfiguring the bar because the screen has changed
        if not self._configured or self._reserved_space_updated or reconfigure:
            Gap._configure(self, qtile, screen)

            if any(self.margin) or any(self.border_width) or self._reserved_space_updated:
                # Increase the margin size for the border. The border will be drawn
                # in this space so the empty space will just be the margin.
                margin = [b + s for b, s in zip(self.border_width, self._reserved_space)]

                if self.horizontal:
                    self.x += margin[3] - self.border_width[3]
                    self.width -= margin[1] + margin[3]
                    self.length = self.width
                    self.fullsize += margin[0] + margin[2]
                    if screen.top is self:
                        self.y += margin[0] - self.border_width[0]
                    else:
                        self.y -= margin[2] + self.border_width[2]

                else:
                    self.y += margin[0] - self.border_width[0]
                    self.height -= margin[0] + margin[2]
                    self.length = self.height
                    self.fullsize += margin[1] + margin[3]
                    if screen.left is self:
                        self.x += margin[3] - self.border_width[3]
                    else:
                        self.x -= margin[1] + self.border_width[1]

            if screen.bottom is self and not self.reserve:
                self.y -= self.height + self.margin[2]
            elif screen.right is self and not self.reserve:
                self.x -= self.width + self.margin[1]

            self._reserved_space_updated = False

        width = self.width + (self.border_width[1] + self.border_width[3])
        height = self.height + (self.border_width[0] + self.border_width[2])

        if self.window:
            # We get _configure()-ed with an existing window when screens are getting
            # reconfigured but this screen is present both before and after
            self.window.place(self.x, self.y, width, height, 0, None)

        else:
            # Whereas we won't have a window if we're startup up for the first time or
            # the window has been killed by us no longer using the bar's screen

            # X11 only:
            # To preserve correct display of SysTray widget, we need a 24-bit
            # window where the user requests an opaque bar.
            if qtile.core.name == "x11":
                depth = (
                    32
                    if has_transparency(self.background)
                    else qtile.core.conn.default_screen.root_depth
                )

                self.window = qtile.core.create_internal(  # type: ignore [call-arg]
                    self.x, self.y, width, height, depth
                )

            else:
                self.window = qtile.core.create_internal(self.x, self.y, width, height)

            self.window.opacity = self.opacity
            self.window.unhide()

            self.window.process_window_expose = self.draw
            self.window.process_button_click = self.process_button_click
            self.window.process_button_release = self.process_button_release
            self.window.process_pointer_enter = self.process_pointer_enter
            self.window.process_pointer_leave = self.process_pointer_leave
            self.window.process_pointer_motion = self.process_pointer_motion
            self.window.process_key_press = self.process_key_press

        if hasattr(self, "drawer"):
            self.drawer.width = width
            self.drawer.height = height
        else:
            self.drawer = self.window.create_drawer(width, height)
        self.drawer.clear(self.background)

        crashed_widgets: set[_Widget] = set()
        qtile.renamed_widgets = []
        if self._configured:
            for i in self.widgets:
                if not self._configure_widget(i):
                    crashed_widgets.add(i)
        else:
            for idx, i in enumerate(self.widgets):
                # Create a mirror if this widget is already configured but isn't a Mirror
                # We don't do isinstance(i, Mirror) because importing Mirror (at the top)
                # would give a circular import as libqtile.widget.base imports lbqtile.bar
                if i.configured and i.__class__.__name__ != "Mirror":
                    i = i.create_mirror()
                    self.widgets[idx] = i
                if self._configure_widget(i):
                    qtile.register_widget(i)
                else:
                    crashed_widgets.add(i)

        # Alert the user that we've renamed some widgets
        if qtile.renamed_widgets:
            logger.info(
                "The following widgets were renamed in qtile.widgets_map: %s "
                "To bind commands, rename the widget or use lazy.widget[new_name].",
                ", ".join(qtile.renamed_widgets),
            )
            qtile.renamed_widgets.clear()

        hook.subscribe.setgroup(self.set_layer)
        hook.subscribe.startup_complete(self.set_layer)

        self._remove_crashed_widgets(crashed_widgets)
        self.draw()
        self._resize(self.length, self.widgets)
        self._configured = True

    def _configure_widget(self, widget: _Widget) -> bool:
        assert self.qtile is not None

        if widget.supported_backends and (self.qtile.core.name not in widget.supported_backends):
            logger.warning(
                "Widget removed: %s does not support %s.",
                widget.__class__.__name__,
                self.qtile.core.name,
            )
            return False

        try:
            widget._configure(self.qtile, self)

            if self.horizontal:
                widget.offsety = self.border_width[0]
            else:
                widget.offsetx = self.border_width[3]

            widget.configured = True
        except Exception:
            logger.exception(
                "%s widget crashed during _configure with error:", widget.__class__.__name__
            )
            return False

        return True

    def _remove_crashed_widgets(self, crashed_widgets: set[_Widget]) -> None:
        if not crashed_widgets:
            return

        assert self.qtile is not None
        from libqtile.widget.config_error import ConfigErrorWidget

        for i in crashed_widgets:
            index = self.widgets.index(i)

            # Widgets that aren't available on the current backend should not
            # be shown as "crashed" as the behaviour is expected. Only notify
            # for genuine crashes.
            if not i.supported_backends or (self.qtile.core.name in i.supported_backends):
                if not i.hide_crash:
                    crash = ConfigErrorWidget(widget=i)
                    crash._configure(self.qtile, self)
                    if self.horizontal:
                        crash.offsety = self.border_width[0]
                    else:
                        crash.offsetx = self.border_width[3]
                    self.widgets.insert(index, crash)

            self.widgets.remove(i)

    def _items(self, name: str) -> ItemT:
        if name == "screen" and self.screen is not None:
            return True, []
        elif name == "widget" and self.widgets:
            return False, [w.name for w in self.widgets]
        return None

    def _select(self, name: str, sel: str | int | None) -> CommandObject | None:
        if name == "screen":
            return self.screen
        elif name == "widget":
            for widget in self.widgets:
                if widget.name == sel:
                    return widget
        return None

    def finalize(self) -> None:
        if self.future:
            self.future.cancel()
        if hasattr(self, "drawer"):
            self.drawer.finalize()
            del self.drawer
        if self.window:
            self.window.kill()
            self.window = None
        self.widgets.clear()

    def _resize(self, length: int, widgets: list[_Widget]) -> None:
        # We want consecutive stretch widgets to split one 'block' of space between them
        stretches = []
        consecutive_stretches: defaultdict[_Widget, list[_Widget]] = defaultdict(list)
        prev_stretch: _Widget | None = None
        for widget in widgets:
            if widget.length_type == STRETCH:
                if prev_stretch:
                    consecutive_stretches[prev_stretch].append(widget)
                else:
                    stretches.append(widget)
                    prev_stretch = widget
            else:
                prev_stretch = None

        if stretches:
            stretchspace = length - sum(i.length for i in widgets if i.length_type != STRETCH)
            stretchspace = max(stretchspace, 0)
            num_stretches = len(stretches)

            if num_stretches == 1:
                stretches[0].length = stretchspace
            else:
                block = 0
                blocks = []
                for i in widgets:
                    if i.length_type != STRETCH:
                        block += i.length
                    elif i in stretches:  # False for consecutive_stretches
                        blocks.append(block)
                        block = 0
                if block:
                    blocks.append(block)
                interval = length // num_stretches

                for idx, i in enumerate(stretches):
                    if idx == 0:
                        i.length = interval - blocks[0] - blocks[1] // 2
                    elif idx == num_stretches - 1:
                        i.length = interval - blocks[-1] - blocks[-2] // 2
                    else:
                        i.length = int(interval - blocks[idx] / 2 - blocks[idx + 1] / 2)
                    stretchspace -= i.length

                stretches[0].length += stretchspace // 2
                stretches[-1].length += stretchspace - stretchspace // 2

            for i, followers in consecutive_stretches.items():
                length = i.length // (len(followers) + 1)
                rem = i.length - length
                i.length = length
                for f in followers:
                    f.length = length
                    rem -= length
                i.length += rem

        if self.horizontal:
            offset = self.border_width[3]
            for i in widgets:
                i.offsetx = offset
                offset += i.length
        else:
            offset = self.border_width[0]
            for i in widgets:
                i.offsety = offset
                offset += i.length

    def get_widget_in_position(self, x: int, y: int) -> _Widget | None:
        if self.horizontal:
            for i in self.widgets:
                if x < i.offsetx + i.length:
                    return i
        else:
            for i in self.widgets:
                if y < i.offsety + i.length:
                    return i
        return None

    def process_button_click(self, x: int, y: int, button: int) -> None:
        assert self.qtile is not None

        # If we're clicking on a bar that's not on the current screen, focus that screen
        if self.screen and self.screen is not self.qtile.current_screen:
            if self.qtile.core.name == "x11" and self.qtile.current_window:
                self.qtile.current_window._grab_click()
            index = self.qtile.screens.index(self.screen)
            self.qtile.focus_screen(index, warp=False)

        widget = self.get_widget_in_position(x, y)
        if widget:
            widget.button_press(
                x - widget.offsetx,
                y - widget.offsety,
                button,
            )

    def process_button_release(self, x: int, y: int, button: int) -> None:
        widget = self.get_widget_in_position(x, y)
        if widget:
            widget.button_release(
                x - widget.offsetx,
                y - widget.offsety,
                button,
            )

    def process_pointer_enter(self, x: int, y: int) -> None:
        widget = self.get_widget_in_position(x, y)
        if widget:
            widget.mouse_enter(
                x - widget.offsetx,
                y - widget.offsety,
            )
        self._has_cursor = widget

    def process_pointer_leave(self, x: int, y: int) -> None:
        if self._has_cursor:
            self._has_cursor.mouse_leave(
                x - self._has_cursor.offsetx,
                y - self._has_cursor.offsety,
            )
            self._has_cursor = None

    def process_pointer_motion(self, x: int, y: int) -> None:
        widget = self.get_widget_in_position(x, y)
        if widget and self._has_cursor and widget is not self._has_cursor:
            self._has_cursor.mouse_leave(
                x - self._has_cursor.offsetx,
                y - self._has_cursor.offsety,
            )
            widget.mouse_enter(
                x - widget.offsetx,
                y - widget.offsety,
            )
        self._has_cursor = widget

    def process_key_press(self, keycode: int) -> None:
        if self._has_keyboard:
            self._has_keyboard.process_key_press(keycode)

    def widget_grab_keyboard(self, widget: _Widget) -> None:
        """
        A widget can call this method to grab the keyboard focus
        and receive keyboard messages. When done,
        widget_ungrab_keyboard() must be called.
        """
        assert self.qtile is not None

        self._has_keyboard = widget
        self._saved_focus = self.qtile.current_window
        if self.window:
            self.window.focus(False)

    def widget_ungrab_keyboard(self) -> None:
        """
        Removes keyboard focus from the widget.
        """
        if self._saved_focus is not None:
            self._saved_focus.focus(False)
        self._has_keyboard = None

    def draw(self) -> None:
        assert self.qtile is not None

        if not self.widgets:
            return  # calling self._actual_draw in this case would cause a NameError.
        if not self._draw_queued:
            # Delay actually drawing the bar until the event loop is idle, and only once
            # even if this method is called multiple times during the same task.
            self.future = self.qtile.call_soon(self._actual_draw)
            self._draw_queued = True

    def _actual_draw(self) -> None:
        self._draw_queued = False
        self._resize(self.length, self.widgets)
        # We draw the border before the widgets
        if any(self.border_width):
            # The border is drawn "outside" of the bar (i.e. not in the space that the
            # widgets occupy) so we need to add the additional space
            width = self.width + self.border_width[1] + self.border_width[3]
            height = self.height + self.border_width[0] + self.border_width[2]

            # line_opts is a list of tuples where each tuple represents the borders
            # in the order N, E, S, W. The border tuple contains two pairs of
            # co-ordinates for the start and end of the border.
            rects = [
                (0, 0, width, self.border_width[0]),
                (
                    width - (self.border_width[1]),
                    self.border_width[0],
                    self.border_width[1],
                    height - self.border_width[0] - self.border_width[2],
                ),
                (0, height - self.border_width[2], width, self.border_width[2]),
                (
                    0,
                    self.border_width[0],
                    self.border_width[3],
                    height - self.border_width[0] - self.border_width[2],
                ),
            ]

            for border_width, colour, rect in zip(self.border_width, self.border_color, rects):
                if not border_width:
                    continue

                # Draw the border
                self.drawer.clear_rect(*rect)
                self.drawer.ctx.rectangle(*rect)
                self.drawer.set_source_rgb(colour)  # type: ignore[arg-type]
                self.drawer.ctx.fill()
                src_x, src_y, width, height = rect

                self.drawer.draw(
                    offsetx=src_x,
                    offsety=src_y,
                    width=width,
                    height=height,
                    src_x=src_x,
                    src_y=src_y,
                )

        for i in self.widgets:
            i.draw()

        # We need to check if there is any unoccupied space in the bar
        # This can happen where there are no SPACER-type widgets to fill
        # empty space.
        # In that scenario, we fill the empty space with the bar background colour
        # We do this, instead of just filling the bar completely at the start of this
        # method to avoid flickering.

        # Widgets are offset by the top/left border but this is not included in self.length
        # so we adjust the end of the bar area for this offset
        if self.horizontal:
            bar_end = self.length + self.border_width[3]
            widget_end = i.offsetx + i.length
        else:
            bar_end = self.length + self.border_width[0]
            widget_end = i.offsety + i.length

        if widget_end < bar_end:
            # Defines a rectangle for the area enclosed by the bar's borders and the end of the
            # last widget.
            if self.horizontal:
                rect = (widget_end, self.border_width[0], bar_end - widget_end, self.height)
            else:
                rect = (self.border_width[3], widget_end, self.width, bar_end - widget_end)

            # Clear that area (i.e. don't clear borders) and fill with background colour
            self.drawer.clear_rect(*rect)
            self.drawer.ctx.rectangle(*rect)
            self.drawer.set_source_rgb(self.background)
            self.drawer.ctx.fill()
            x, y, w, h = rect
            self.drawer.draw(offsetx=x, offsety=y, height=h, width=w, src_x=x, src_y=y)

    @expose_command()
    def info(self) -> dict[str, Any]:
        return dict(
            length=self.length,
            size=self.size,
            fullsize=self.fullsize,
            width=self.width,
            height=self.height,
            position=self.position,
            widgets=[i.info() for i in self.widgets],
            window=self.window.wid if self.window else None,
        )

    def is_show(self) -> bool:
        return self.fullsize != 0

    def show(self, is_show: bool = True) -> None:
        if is_show != self.is_show():
            if is_show:
                self.fullsize = self._saved_size
                if self.window:
                    self.window.unhide()
            else:
                self._saved_size = self.fullsize
                self.fullsize = 0
                if self.window:
                    self.window.hide()
            if self.screen and self.screen.group:
                self.screen.group.layout_all()

    def adjust_reserved_space(self, size: int) -> None:
        if self.fullsize:
            # is this necessary?
            self.fullsize = self.size

        for i, side in enumerate(NESW):
            if getattr(self.screen, side) is self:
                self._reserved_space[i] += size
            if self._reserved_space[i] < 0:
                raise ValueError("Gap/Bar can't reserve negative space.")

        self._reserved_space_updated = True

    @expose_command()
    def fake_button_press(self, x: int, y: int, button: int = 1) -> None:
        """
        Fake a mouse-button-press on the bar. Coordinates are relative
        to the top-left corner of the bar.

        Parameters
        ==========
        x :
            X coordinate of the mouse button press.
        y :
            Y coordinate of the mouse button press.
        button:
            Mouse button, for more details, see :ref:`mouse-events`.
        """
        self.process_button_click(x, y, button)

    def set_layer(self) -> None:
        if self.window:
            if self.reserve:
                self.window.keep_below(enable=True)
            else:
                # Bar is not reserving screen space so let's keep above other windows
                self.window.keep_above(enable=True)


BarType = Bar | Gap
