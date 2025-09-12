from __future__ import annotations

import typing

import libqtile.backend.base.window as base
from libqtile import hook, utils
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.drawer import Drawer
from libqtile.command.base import CommandError, expose_command
from libqtile.core.manager import Qtile
from libqtile.group import _Group
from libqtile.log_utils import logger
from libqtile.utils import ColorsType, rgb

try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")
    # Continue if ffi not built, so that docs can be built without wayland deps.
    # Provide a stub for FFI to keep going
    from libqtile.backend.wayland.ffi_stub import ffi, lib

if typing.TYPE_CHECKING:
    from libqtile.command.base import CommandObject, ItemT


class Base(base._Window):
    def __init__(self, qtile: Qtile, ptr: ffi.CData, wid: int):
        base._Window.__init__(self)
        self.qtile = qtile
        self._group: _Group | None = None
        # TODO: why are there 2 groups here?
        self._ptr = ptr
        self._wid = wid
        self._wm_class: str | None = None
        self.bordercolor: ColorsType | None = None
        # TODO: what is this?
        self.defunct = False
        self.group: _Group | None = None

    def reparent(self, layer: int) -> None:
        if self.layer == layer:
            return
        lib.qw_view_reparent(self._ptr, layer)

    @expose_command()
    def bring_to_front(self) -> None:
        self.reparent(lib.LAYER_BRINGTOFRONT)
        lib.qw_view_raise_to_top(self._ptr)

    @property
    def wid(self) -> int:
        return self._wid

    @property
    def x(self) -> int:
        return self._ptr.x

    @x.setter
    def x(self, x: int) -> None:
        self._ptr.x = x

    @property
    def y(self) -> int:
        return self._ptr.y

    @y.setter
    def y(self, y: int) -> None:
        self._ptr.y = y

    @property
    def width(self) -> int:
        return self._ptr.width

    @width.setter
    def width(self, width: int) -> None:
        self._ptr.width = width

    @property
    def height(self) -> int:
        return self._ptr.height

    @height.setter
    def height(self, height: int) -> None:
        self._ptr.height = height

    @property
    def _borderwidth(self) -> int:
        return self._ptr.bn

    @expose_command()
    def info(self) -> dict:
        """Return a dictionary of info."""
        # TODO: complete implementation
        float_info = {
            "x": self.float_x,
            "y": self.float_y,
            "width": self._float_width,
            "height": self._float_height,
        }
        return dict(
            name=self.name,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            group=self.group.name if self.group else None,
            id=self.wid,
            wm_class=self.get_wm_class(),
            # shell can be either "XDG" or "XWayland" or "layer"?
            shell=ffi.string(self._ptr.shell).decode() if self._ptr.shell != ffi.NULL else "",
            float_info=float_info,
            floating=self._float_state != FloatStates.NOT_FLOATING,
            maximized=self._float_state == FloatStates.MAXIMIZED,
            minimized=self._float_state == FloatStates.MINIMIZED,
            fullscreen=self._float_state == FloatStates.FULLSCREEN,
        )

    def kill(self) -> None:
        self._ptr.kill(self._ptr)

    def hide(self) -> None:
        self._ptr.hide(self._ptr)

    def unhide(self) -> None:
        self._ptr.unhide(self._ptr)

    @expose_command()
    def place(
        self,
        x: int | None,
        y: int | None,
        width: int | None,
        height: int | None,
        borderwidth: int | None = None,
        bordercolor: ColorsType | None = None,
        above: bool = False,
        margin: int | list[int] | None = None,
        respect_hints: bool = False,
    ) -> None:
        # Adjust the placement to account for layout margins, if there are any.
        # TODO: is respect_hints only for X11?
        assert ffi is not None
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        if bordercolor is None:
            bordercolor = self.bordercolor
        if borderwidth is None:
            borderwidth = self._borderwidth
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        # TODO: respect hints

        if self.group is not None and self.group.screen is not None:
            self.float_x = x - self.group.screen.x
            self.float_y = y - self.group.screen.y
        n = 0
        c_layers = ffi.NULL
        if bordercolor is not None:
            if isinstance(bordercolor, list):
                # multiple border colors
                if all(isinstance(x, str) or isinstance(x, tuple) for x in bordercolor):
                    colors = bordercolor
                else:
                    pass
                    # TODO: Check validation logic, handle this case
            else:
                colors = [bordercolor]
            n = len(colors)

            # Allocate array of qw_border
            c_layers = ffi.new(f"struct qw_border[{n}]")

            base_width = borderwidth // n
            remainder = borderwidth % n

            for i, bc in enumerate(colors):
                # Set type RECT
                c_layers[i].type = lib.QW_BORDER_RECT

                # Set width, distribute remainder
                c_layers[i].width = base_width + (1 if i < remainder else 0)

                # Convert python color to RGBA float[4]
                rgba = rgb(bc)

                # Copy RGBA into c struct color field
                # Each edge is set to the same colour
                for side in range(4):
                    for j in range(4):
                        c_layers[i].rect.color[side][j] = rgba[j]

        self.bordercolor = bordercolor
        self._ptr.place(self._ptr, x, y, width, height, c_layers, n, int(above))

    @expose_command()
    def focus(self, warp: bool = True) -> None:
        self.qtile.core.focus_window(self)

        # TODO
        # Call core.warp_pointer() previously here

        if self.group and self.group.current_window is not self:
            self.group.focus(self)

        hook.fire("client_focus", self)


class Internal(Base, base.Internal):
    def __init__(self, qtile: Qtile, ptr: ffi.CData, wid: int):
        Base.__init__(self, qtile, lib.qw_internal_view_get_base(ptr), wid)
        base.Internal.__init__(self)
        ptr.base.wid = wid
        self._internal_ptr = ptr

    @property
    def surface(self) -> ffi.CData:
        return ffi.cast("void *", self._internal_ptr.image_surface)

    def finalize(self) -> None:
        self.hide()

    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""
        return Drawer(self.qtile, self, width, height)

    def set_buffer_with_damage(self, offsetx: int, offsety: int, width: int, height: int) -> None:
        lib.qw_internal_view_set_buffer_with_damage(
            self._internal_ptr, offsetx, offsety, width, height
        )

    @expose_command()
    def kill(self) -> None:
        super().kill()
        if self.wid in self.qtile.windows_map:
            # It will be present during config reloads; absent during shutdown as this
            # will follow graceful_shutdown
            del self.qtile.windows_map[self.wid]

    @expose_command()
    def info(self) -> dict:
        """Return a dictionary of info."""
        return dict(
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            id=self.wid,
        )


@ffi.def_extern()
def request_focus_cb(userdata: ffi.CData) -> int:
    win = ffi.from_handle(userdata)
    if win.handle_request_focus():
        return 1
    return 0


@ffi.def_extern()
def request_close_cb(userdata: ffi.CData) -> int:
    win = ffi.from_handle(userdata)
    if win.handle_request_close():
        return 1
    return 0


@ffi.def_extern()
def request_fullscreen_cb(fullscreen: bool, userdata: ffi.CData) -> int:
    win = ffi.from_handle(userdata)
    if win.handle_request_fullscreen(fullscreen):
        return 1
    return 0


@ffi.def_extern()
def request_maximize_cb(maximize: bool, userdata: ffi.CData) -> int:
    win = ffi.from_handle(userdata)
    if win.handle_request_maximize(maximize):
        return 1
    return 0


@ffi.def_extern()
def request_minimize_cb(minimize: bool, userdata: ffi.CData) -> int:
    win = ffi.from_handle(userdata)
    if win.handle_request_minimize(minimize):
        return 1
    return 0


@ffi.def_extern()
def set_title_cb(title: ffi.CData, userdata: ffi.CData) -> None:
    win = ffi.from_handle(userdata)
    win.handle_set_title(ffi.string(title).decode())


@ffi.def_extern()
def set_app_id_cb(app_id: ffi.CData, userdata: ffi.CData) -> None:
    win = ffi.from_handle(userdata)
    win.handle_set_app_id(ffi.string(app_id).decode())


class Window(Base, base.Window):
    def __init__(self, qtile: Qtile, ptr: ffi.CData, wid: int):
        Base.__init__(self, qtile, ptr, wid)
        base.Window.__init__(self)

        self.float_x: int | None = None
        self.float_y: int | None = None
        self._float_width: int = 0
        self._float_height: int = 0
        self._float_state = FloatStates.NOT_FLOATING
        # TODO: destroy?
        self._userdata = ffi.new_handle(self)
        ptr.cb_data = self._userdata
        ptr.request_focus_cb = lib.request_focus_cb
        ptr.request_close_cb = lib.request_close_cb
        ptr.request_maximize_cb = lib.request_maximize_cb
        ptr.request_minimize_cb = lib.request_minimize_cb
        ptr.request_fullscreen_cb = lib.request_fullscreen_cb
        ptr.set_title_cb = lib.set_title_cb
        ptr.set_app_id_cb = lib.set_app_id_cb

    @property
    def layer(self) -> int:
        return self._ptr.layer

    @expose_command()
    def keep_above(self, enable: bool | None = None) -> None:
        is_enabled = self.layer == lib.LAYER_KEEPABOVE
        if enable is None:
            enable = not is_enabled

        if enable:
            self.reparent(lib.LAYER_KEEPABOVE)
        else:
            self.reparent(lib.LAYER_LAYOUT)

    @expose_command()
    def keep_below(self, enable: bool | None = None) -> None:
        is_enabled = self.layer == lib.LAYER_KEEPBELOW
        if enable is None:
            enable = not is_enabled

        if enable:
            self.reparent(lib.LAYER_KEEPBELOW)
        else:
            self.reparent(lib.LAYER_LAYOUT)

    @expose_command()
    def move_to_top(self) -> None:
        lib.qw_view_raise_to_top(self._ptr)

    @expose_command()
    def move_up(self, force: bool = False) -> None:
        if force and self.layer == lib.LAYER_KEEPBELOW:
            new_layer = self.get_new_layer(self._float_state)
            self.reparent(new_layer)
        lib.qw_view_move_up(self._ptr)

    @expose_command()
    def move_down(self, force: bool = False) -> None:
        if force and self.layer == lib.LAYER_KEEPAOVE:
            new_layer = self.get_new_layer(self._float_state)
            self.reparent(new_layer)
        lib.qw_view_move_down(self._ptr)

    @expose_command()
    def move_to_bottom(self) -> None:
        lib.qw_view_lower_to_bottom(self._ptr)

    def handle_request_focus(self) -> bool:
        self.focus()
        return True

    def handle_request_close(self) -> bool:
        self.kill()
        return True

    def handle_request_fullscreen(self, fullscreen: bool) -> bool:
        if self.qtile.config.auto_fullscreen:
            if self.fullscreen != fullscreen:
                self.fullscreen = fullscreen
                return True
        return False

    def handle_request_maximize(self, maximize: bool) -> bool:
        self.maximized = maximize
        return True

    def handle_request_minimize(self, minimize: bool) -> bool:
        self.minimized = minimize
        return True

    def handle_set_title(self, title: str) -> None:
        logger.debug("Signal: xdgwindow set_title")
        if title != self.name:
            self.name = title
            # TODO: Handle foreign-toplevel-management?
            hook.fire("client_name_updated", self)

    def handle_set_app_id(self, app_id: str) -> None:
        logger.debug("Signal: xdgwindow set_app_id")
        self._wm_class = app_id
        # TODO: Handle foreign-toplevel-management?

    def get_wm_class(self) -> list | None:
        if self._wm_class:
            return [self._wm_class]
        return None

    @expose_command()
    def is_visible(self) -> bool:
        return lib.qw_view_is_visible(self._ptr)

    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        # The concrete Window class must fire the client_managed hook after it's
        # completed any custom logic.
        self.defunct = True
        if self.group:
            self.group.remove(self)

        # Keep track of user-specified geometry to support X11.
        # Respect configure requests only if these are `None` here.
        conf_x = x
        conf_y = y
        conf_width = width
        conf_height = height

        if x is None:
            x = self.x + self.borderwidth
        if y is None:
            y = self.y + self.borderwidth
        if width is None:
            width = self.width
        if height is None:
            height = self.height

        win = self._to_static(conf_x, conf_y, conf_width, conf_height)

        # Remove references to original window
        self._userdata = None

        # TODO: pass over ftm

        if screen is not None:
            win.screen = self.qtile.screens[screen]
        win.unhide()
        win.place(x, y, width, height, 0, None)
        self.qtile.windows_map[self.wid] = win

        # TODO: pointer constraints

        hook.fire("client_managed", win)

    def _to_static(
        self, x: int | None, y: int | None, width: int | None, height: int | None
    ) -> Static:
        return Static(
            self.qtile,
            self._ptr,
            self._wid,
        )

    def togroup(
        self, group_name: str | None = None, switch_group: bool = False, toggle: bool = False
    ) -> None:
        """
        Move window to a specified group

        Also switch to that group if switch_group is True.

        If `toggle` is True and and the specified group is already on the screen,
        use the last used group as target instead.
        """
        if group_name is None:
            group = self.qtile.current_group
        else:
            if group_name not in self.qtile.groups_map:
                raise CommandError(f"No such group: {group_name}")
            group = self.qtile.groups_map[group_name]

        if self.group is group:
            if toggle and self.group.screen.previous_group:
                group = self.group.screen.previous_group
            else:
                return

        self.hide()
        if self.group:
            if self.group.screen:
                # for floats remove window offset
                self.x -= self.group.screen.x
            group_ref = self.group
            self.group.remove(self)
            # delete groups with `persist=False`
            if (
                not self.qtile.dgroups.groups_map[group_ref.name].persist
                and len(group_ref.windows) <= 1
            ):
                # set back original group so _del() can grab it
                self.group = group_ref
                self.qtile.dgroups._del(self)
                self.group = None

        if group.screen and self.x < group.screen.x:
            self.x += group.screen.x
        group.add(self)
        if switch_group:
            group.toscreen(toggle=toggle)

    def _items(self, name: str) -> ItemT:
        if name == "group":
            return True, []
        if name == "layout":
            if self.group:
                return True, list(range(len(self.group.layouts)))
            return None
        if name == "screen":
            if self.group and self.group.screen:
                return True, []
        return None

    def _select(self, name: str, sel: str | int | None) -> CommandObject | None:
        if name == "group":
            return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout if self.group else None
            else:
                return utils.lget(self.group.layouts, int(sel)) if self.group else None
        elif name == "screen":
            return self.group.screen if self.group else None
        return None

    @property
    def group(self) -> _Group | None:
        return self._group

    @group.setter
    def group(self, group: _Group | None) -> None:
        self._group = group

    @expose_command()
    def get_position(self) -> tuple[int, int]:
        return int(self._ptr.x), int(self._ptr.y)

    @expose_command()
    def get_size(self) -> tuple[int, int]:
        return int(self._ptr.width), int(self._ptr.height)

    def get_pid(self) -> int:
        return int(self._ptr.get_pid(self._ptr))

    def get_new_layer(self, state: FloatStates) -> int:
        if self.qtile.config.floats_kept_above and state == FloatStates.FLOATING:
            return lib.LAYER_KEEPABOVE
        if state == FloatStates.MAXIMIZED:
            return lib.LAYER_MAX
        if state == FloatStates.FULLSCREEN:
            return lib.LAYER_FULLSCREEN
        return lib.LAYER_LAYOUT

    @property
    def floating(self) -> bool:
        return self._float_state != FloatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float: bool) -> None:
        if do_float and self._float_state == FloatStates.NOT_FLOATING:
            if self.is_placed():
                screen = self.group.screen  # type: ignore[union-attr] # see is_placed()
                if not self._float_width:  # These might start as 0
                    self._float_width = self.width
                    self._float_height = self.height
                self._reconfigure_floating(
                    screen.x + self.float_x,
                    screen.y + self.float_y,
                    self._float_width,
                    self._float_height,
                )
            else:
                # if we are setting floating early, e.g. from a hook, we don't have a screen yet
                self._float_state = FloatStates.FLOATING
        elif (not do_float) and self._float_state != FloatStates.NOT_FLOATING:
            self.reparent(lib.LAYER_LAYOUT)
            self._update_fullscreen(False)
            self._update_maximized(False)
            self._update_minimized(False)
            if self._float_state == FloatStates.FLOATING:
                # store last size
                self._float_width = self.width
                self._float_height = self.height
            self._float_state = FloatStates.NOT_FLOATING
            if self.group:
                self.group.mark_floating(self, False)
            hook.fire("float_change")

    @property
    def fullscreen(self) -> bool:
        return self._float_state == FloatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full: bool) -> None:
        if do_full and self._float_state != FloatStates.FULLSCREEN:
            screen = (self.group and self.group.screen) or self.qtile.find_closest_screen(
                self.x, self.y
            )

            if self._float_state not in (FloatStates.MAXIMIZED, FloatStates.FULLSCREEN):
                self._save_geometry()

            bw = self.group.floating_layout.fullscreen_border_width if self.group else 0
            self._reconfigure_floating(
                screen.x,
                screen.y,
                screen.width - 2 * bw,
                screen.height - 2 * bw,
                new_float_state=FloatStates.FULLSCREEN,
            )
        elif self._float_state == FloatStates.FULLSCREEN:
            self._restore_geometry()
            self.floating = False

    def _update_fullscreen(self, do_full: bool) -> None:
        if do_full != (self._float_state == FloatStates.FULLSCREEN):
            self._ptr.update_fullscreen(self._ptr, do_full)

    @property
    def maximized(self) -> bool:
        return self._float_state == FloatStates.MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize: bool) -> None:
        if do_maximize:
            screen = (self.group and self.group.screen) or self.qtile.find_closest_screen(
                self.x, self.y
            )

            if self._float_state not in (FloatStates.MAXIMIZED, FloatStates.FULLSCREEN):
                self._save_geometry()

            bw = self.group.floating_layout.max_border_width if self.group else 0
            self._reconfigure_floating(
                screen.dx,
                screen.dy,
                screen.dwidth - 2 * bw,
                screen.dheight - 2 * bw,
                new_float_state=FloatStates.MAXIMIZED,
            )
        else:
            if self._float_state == FloatStates.MAXIMIZED:
                self._restore_geometry()
                self.floating = False

    def _update_maximized(self, do_max: bool) -> None:
        if do_max != (self._float_state == FloatStates.MAXIMIZED):
            self._ptr.update_maximized(self._ptr, do_max)

    @property
    def minimized(self) -> bool:
        return self._float_state == FloatStates.MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize: bool) -> None:
        if do_minimize:
            if self._float_state != FloatStates.MINIMIZED:
                self._reconfigure_floating(new_float_state=FloatStates.MINIMIZED)
        else:
            if self._float_state == FloatStates.MINIMIZED:
                self.floating = False

    def _update_minimized(self, do_min: bool) -> None:
        if do_min != (self._float_state == FloatStates.MINIMIZED):
            self._ptr.update_minimized(self._ptr, do_min)

    def _reconfigure_floating(
        self,
        x: int | None = None,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
        new_float_state: FloatStates = FloatStates.FLOATING,
    ) -> None:
        self._update_fullscreen(new_float_state == FloatStates.FULLSCREEN)
        self._update_maximized(new_float_state == FloatStates.MAXIMIZED)
        self._update_minimized(new_float_state == FloatStates.MINIMIZED)
        if new_float_state == FloatStates.MINIMIZED:
            self.hide()
        else:
            self.place(
                x, y, w, h, self._borderwidth, self.bordercolor, above=True, respect_hints=True
            )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            self.reparent(self.get_new_layer(new_float_state))
            if self.group:  # may be not, if it's called from hook
                self.group.mark_floating(self, True)
            hook.fire("float_change")

    def _tweak_float(
        self,
        x: int | None = None,
        y: int | None = None,
        dx: int = 0,
        dy: int = 0,
        w: int | None = None,
        h: int | None = None,
        dw: int = 0,
        dh: int = 0,
    ) -> None:
        if x is None:
            x = self.x
        x += dx

        if y is None:
            y = self.y
        y += dy

        if w is None:
            w = self.width
        w += dw

        if h is None:
            h = self.height
        h += dh

        if h < 0:
            h = 0
        if w < 0:
            w = 0

        screen = self.qtile.find_closest_screen(x + w // 2, y + h // 2)
        if self.group and screen is not None and screen != self.group.screen:
            self.group.remove(self, force=True)
            screen.group.add(self, force=True)
            self.qtile.focus_screen(screen.index)

        self._reconfigure_floating(x, y, w, h)

    @expose_command()
    def move_floating(self, dx: int, dy: int) -> None:
        self._tweak_float(dx=dx, dy=dy)

    @expose_command()
    def resize_floating(self, dw: int, dh: int) -> None:
        self._tweak_float(dw=dw, dh=dh)

    @expose_command()
    def set_position_floating(self, x: int, y: int) -> None:
        self._tweak_float(x=x, y=y)

    @expose_command()
    def set_position(self, x: int, y: int) -> None:
        if self.floating:
            self._tweak_float(x=x, y=y)
            return

        if self.group:
            cx = self.qtile.core.qw_cursor.cursor.x
            cy = self.qtile.core.qw_cursor.cursor.y
            for window in self.group.windows:
                if (
                    window is not self
                    and not window.floating
                    and window.x <= cx <= (window.x + window.width)
                    and window.y <= cy <= (window.y + window.height)
                ):
                    self.group.layout.swap(self, window)
                    return

    @expose_command()
    def set_size_floating(self, w: int, h: int) -> None:
        self._tweak_float(w=w, h=h)

    @expose_command()
    def toggle_floating(self) -> None:
        self.floating = not self.floating

    @expose_command()
    def enable_floating(self) -> None:
        self.floating = True

    @expose_command()
    def disable_floating(self) -> None:
        self.floating = False

    @expose_command()
    def toggle_maximize(self) -> None:
        self.maximized = not self.maximized

    @expose_command()
    def toggle_minimize(self) -> None:
        self.minimized = not self.minimized

    @expose_command()
    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen

    @expose_command()
    def enable_fullscreen(self) -> None:
        self.fullscreen = True

    @expose_command()
    def disable_fullscreen(self) -> None:
        self.fullscreen = False


class Static(Base, base.Static):
    def __init__(self, qtile: Qtile, ptr: ffi.CData, wid: int):
        Base.__init__(self, qtile, ptr, wid)
        base.Static.__init__(self)
        self.screen = qtile.current_screen
        self.x = 0
        self.y = 0
        self._width = 0
        self._height = 0
        self._urgent = False
        # TODO: opacity, idle_inhibitors, ftm

        self._userdata = ffi.new_handle(self)
        ptr.cb_data = self._userdata
        ptr.request_focus_cb = ffi.NULL
        ptr.request_close_cb = ffi.NULL
        ptr.request_maximize_cb = ffi.NULL
        ptr.request_minimize_cb = ffi.NULL
        ptr.request_fullscreen_cb = ffi.NULL
        ptr.set_title_cb = lib.set_title_cb
        ptr.set_app_id_cb = lib.set_app_id_cb

        if self._ptr.title != ffi.NULL:
            self.name = ffi.string(self._ptr.title).decode()
        if self._ptr.app_id != ffi.NULL:
            self._wm_class = ffi.string(self._ptr.app_id).decode()

    def handle_set_title(self, title: str) -> None:
        logger.debug("Signal: static window set_title")
        if title != self.name:
            self.name = title
            # TODO: Handle foreign-toplevel-management?
            hook.fire("client_name_updated", self)

    def handle_set_app_id(self, app_id: str) -> None:
        logger.debug("Signal: static window set_app_id")
        self._wm_class = app_id
        # TODO: Handle foreign-toplevel-management?

    @property
    def wid(self) -> int:
        return self._wid

    def place(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        borderwidth: int,
        bordercolor: ColorsType | None,
        above: bool = False,
        margin: int | list[int] | None = None,
        respect_hints: bool = False,
    ) -> None:
        self.x = x
        self.y = y
        self._width = width
        self._height = height

        n = 0
        self._ptr.place(self._ptr, x, y, width, height, ffi.NULL, n, int(above))

    @expose_command()
    def info(self) -> dict:
        """Return a dictionary of info."""
        info = base.Static.info(self)
        info["shell"] = (
            ffi.string(self._ptr.shell).decode() if self._ptr.shell != ffi.NULL else "",
        )
        return info
