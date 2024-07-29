from typing import TYPE_CHECKING
from libqtile import hook
from libqtile.group import _Group
from libqtile.core.manager import Qtile
import libqtile.backend.base.window as base
from libqtile.backend.wayland.drawer import Drawer
from libqtile.backend.base import FloatStates
from libqtile.command.base import CommandError, expose_command
from libqtile.utils import rgb, ColorsType

ffi = None
lib = None
try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib
except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")


class Base(base._Window):
    def __init__(self, qtile: Qtile, ptr, wid):
        base._Window.__init__(self)
        self.qtile = qtile
        self._group = None
        self._ptr = ptr
        self._wid = wid
        self.bordercolor = None
        # TODO: what is this?
        self.defunct = False
        self.group = None

    @property
    def wid(self):
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
        # TODO: implement
        return {}

    @expose_command()
    def bring_to_front(self) -> None:
        self._ptr.bring_to_front(self._ptr)

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
        c_bordercolor_ptr = ffi.NULL
        n = 0
        if bordercolor is not None:
            colors = [bordercolor]
            # multiple border colors
            if isinstance(bordercolor, list) and all(
                isinstance(x, str) or isinstance(x, tuple) for x in bordercolor
            ):
                colors = bordercolor
            n = len(colors)

            c_bordercolor = ffi.new(f"float[{n}][4]")
            i = 0
            for bc in colors:
                # TODO: mypy type error
                c_bordercolor[i] = ffi.new("float[4]", rgb(bc))
                i += 1

            c_bordercolor_ptr = ffi.cast("float(*)[4]", c_bordercolor)
        self.bordercolor = bordercolor
        self._ptr.place(
            self._ptr, x, y, width, height, borderwidth, c_bordercolor_ptr, n, int(above)
        )

    @expose_command()
    def focus(self, warp: bool = True) -> None:
        self._ptr.focus(self._ptr, int(warp))


class Internal(Base, base.Internal):
    def __init__(self, qtile: Qtile, ptr, wid):
        Base.__init__(self, qtile, lib.qw_internal_view_get_base(ptr), wid)
        base.Internal.__init__(self)
        self._internal_ptr = ptr

    @property
    def surface(self):
        return self._internal_ptr.image_surface

    def finalize(self) -> None:
        self.hide()

    def create_drawer(self, width: int, height: int) -> Drawer:
        """Create a Drawer that draws to this window."""
        return Drawer(self.qtile, self, width, height)

    def set_buffer_with_damage(self, offsetx, offsety, width, height):
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


class Window(Base, base.Window):
    def __init__(self, qtile: Qtile, ptr, wid):
        Base.__init__(self, qtile, ptr, wid)
        base.Window.__init__(self)
        # TODO
        self.name = "TODO"

        self.float_x: int | None = None
        self.float_y: int | None = None
        self._float_width: int = 0
        self._float_height: int = 0
        self._float_state = FloatStates.NOT_FLOATING

    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        # TODO: implement
        return

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

    @property
    def group(self) -> _Group | None:
        return self._group

    @group.setter
    def group(self, group) -> None:
        self._group = group

    @expose_command()
    def get_position(self) -> tuple[int, int]:
        return int(self._ptr.x), int(self._ptr.y)

    @expose_command()
    def get_size(self) -> tuple[int, int]:
        return int(self._ptr.width), int(self._ptr.height)

    def get_pid(self) -> int:
        return int(self._ptr.get_pid())

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
            self._update_fullscreen(False)
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
        # TODO
        pass

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

        # TODO: set maximized in c backend

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

        # TODO: set minimize in c backend

    def _reconfigure_floating(
        self,
        x: int | None = None,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
        new_float_state: FloatStates = FloatStates.FLOATING,
    ) -> None:
        self._update_fullscreen(new_float_state == FloatStates.FULLSCREEN)
        if new_float_state == FloatStates.MINIMIZED:
            self.hide()
        else:
            self.place(
                x, y, w, h, self._borderwidth, self.bordercolor, above=True, respect_hints=True
            )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
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
        self.place(
            x,
            y,
            self.width,
            self.height,
            self._borderwidth,
            self.bordercolor,
        )

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
