# Copyright (c) 2021 Matt Colligan
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

from xcffib.xproto import ConfigWindow

from wlroots import xwayland
from wlroots.wlr_types import SceneTree

from libqtile import hook
from libqtile.backend import base
from libqtile.backend.base import FloatStates
from libqtile.backend.wayland.window import Static, Window
from libqtile.command.base import expose_command
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from typing import Any

    import wlroots.wlr_types.foreign_toplevel_management_v1 as ftm
    from pywayland.server import Listener
    from wlroots.xwayland import SurfaceConfigureEvent

    from libqtile.backend.wayland.core import Core
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorsType


class XWindow(Window[xwayland.Surface]):
    """An X11 client connecting via XWayland."""

    def __init__(self, core: Core, qtile: Qtile, surface: xwayland.Surface):
        Window.__init__(self, core, qtile, surface)
        self._wm_class = self.surface.wm_class

        # Wait until we get a surface when mapping before making a tree
        self.tree: SceneTree | None = None

        # Update the name if the client has set one
        if title := surface.title:
            self.name = title

        # Add some listeners
        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.request_activate_event, self._on_request_activate)
        self.add_listener(surface.request_configure_event, self._on_request_configure)
        self.add_listener(surface.destroy_event, self._on_destroy)

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        if self.floating:
            state = self.surface.surface.current
            if state.width != self._width or state.height != self._height:
                self.place(
                    self.x, self.y, state.width, state.height, self.borderwidth, self.bordercolor
                )

    def _on_request_activate(self, _listener: Listener, event: SurfaceConfigureEvent) -> None:
        logger.debug("Signal: xwindow request_activate")
        self.surface.activate(True)

    def _on_request_configure(self, _listener: Listener, event: SurfaceConfigureEvent) -> None:
        logger.debug("Signal: xwindow request_configure")
        if self.floating:
            self.place(
                event.x, event.y, event.width, event.height, self.borderwidth, self.bordercolor
            )
        else:
            # TODO: We shouldn't need this first configure event, but some clients (e.g.
            # Ardour) seem to freeze up if we pass the current state, which is what we
            # want, and do with `self.place`.
            self.surface.configure(event.x, event.y, event.width, event.height)
            self.place(
                self.x, self.y, self.width, self.height, self.borderwidth, self.bordercolor
            )

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow unmap")
        self.hide()

        # If X11 clients unmap themselves, we stop managing them as we normally do. See
        # The X core's handler for UnmapNotify. Here, we restore them to a pending
        # state.
        if self not in self.core.pending_windows:
            self.finalize_listeners()
            if self.group and self not in self.group.windows:
                self.group = None
            self.qtile.unmanage(self.wid)
            self.core.pending_windows.add(self)
            self._wid = -1
            # Restore the listeners that we set up in __init__
            self.add_listener(self.surface.map_event, self._on_map)
            self.add_listener(self.surface.unmap_event, self._on_unmap)
            self.add_listener(self.surface.request_configure_event, self._on_request_configure)
            self.add_listener(self.surface.destroy_event, self._on_destroy)

        if self.ftm_handle:
            self.ftm_handle.destroy()
            self.ftm_handle = None

        self.core.remove_pointer_constraints(self)

    def _on_request_fullscreen(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow request_fullscreen")
        if self.qtile.config.auto_fullscreen:
            self.fullscreen = not self.fullscreen

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow set_title")
        title = self.surface.title
        if title and title != self.name:
            self.name = title
            if self.ftm_handle:
                self.ftm_handle.set_title(title)
            hook.fire("client_name_updated", self)

    def _on_set_class(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xwindow set_class")
        self._wm_class = self.surface.wm_class
        if self.ftm_handle:
            self.ftm_handle.set_app_id(self._wm_class or "")

    def hide(self) -> None:
        super().hide()

        if self.tree:
            self.tree.node.destroy()
            self.tree = None

            # We stop listening for commit events when unmapped, as the underlying
            # surface can get destroyed by the client.
            self.finalize_listener(self.surface.surface.commit_event)

    def unhide(self) -> None:
        if self not in self.core.pending_windows:
            if self.group and self.group.screen:
                # Only when mapping does the xwayland_surface have a wlr_surface that we can
                # listen for commits on and create a tree for.
                self.add_listener(self.surface.surface.commit_event, self._on_commit)
                if not self.tree:
                    self.tree = SceneTree.subsurface_tree_create(
                        self.container, self.surface.surface
                    )
                    self.tree.node.set_position(self.borderwidth, self.borderwidth)

                self.container.node.set_enabled(enabled=True)
                # Hack: This is to fix pointer focus on xwayland dialogs
                # We previously did bring_to_front here but then that breaks fullscreening (xwayland windows will always be on top)
                # So we now only restack the surface
                # This means that if the dialog is behind the xwayland toplevel (and bring front click being false), focus might break
                # We need to fix this properly with z layering
                self.surface.restack(None, 0)  # XCB_STACK_MODE_ABOVE
                return

        # This is the first time this window has mapped, so we need to do some initial
        # setup.
        self.core.pending_windows.remove(self)
        self._wid = self.core.new_wid()
        logger.debug("Managing new XWayland window with window ID: %s", self._wid)
        surface = self.surface

        # Now we have a surface, we can create the scene-graph node to contain it
        self.tree = SceneTree.subsurface_tree_create(self.container, surface.surface)

        # Make it static if it isn't a regular window (i.e. a window that the X11
        # backend would consider un
        if surface.override_redirect:
            self.static(None, surface.x, surface.y, surface.width, surface.height)
            win = self.qtile.windows_map[self._wid]
            assert isinstance(win, XStatic)
            self.core.focus_window(win)
            win.bring_to_front()
            return

        # Save the CData handle that references this object on the XWayland surface.
        surface.data = self.data_handle

        # Now that the xwayland_surface has a wlr_surface we can add a commit
        # listener. And now that we have `self.tree`, we can accept fullscreen
        # requests.
        self.add_listener(surface.surface.commit_event, self._on_commit)
        self.add_listener(surface.request_fullscreen_event, self._on_request_fullscreen)
        # And it doesn't mean make sense to listen to these until we manage this
        # window
        self.add_listener(surface.set_title_event, self._on_set_title)
        self.add_listener(surface.set_class_event, self._on_set_class)

        # Save the client's desired geometry. xterm seems to have these set to 1, so
        # let's ignore 1 or below. The float sizes will be fetched when it is floated.
        if surface.width > 1:
            self._width = self._float_width = surface.width
        if surface.height > 1:
            self._height = self._float_height = surface.height

        # Set up the foreign toplevel handle
        handle = self.ftm_handle = self.core.foreign_toplevel_manager_v1.create_handle()
        self.add_listener(handle.request_maximize_event, self._on_foreign_request_maximize)
        self.add_listener(handle.request_minimize_event, self._on_foreign_request_minimize)
        self.add_listener(handle.request_activate_event, self._on_foreign_request_activate)
        self.add_listener(handle.request_fullscreen_event, self._on_foreign_request_fullscreen)
        self.add_listener(handle.request_close_event, self._on_foreign_request_close)

        # Get the client's name and class
        if title := surface.title:
            self.name = title
            handle.set_title(title)
        self._wm_class = surface.wm_class
        handle.set_app_id(self._wm_class or "")

        # Now the window is ready to be mapped, we can go ahead and manage it. Map
        # it first so that we end end up recursing into this signal handler again.
        self.qtile.manage(self)
        if self.group and self.group.screen:
            self.core.focus_window(self)

    @expose_command()
    def kill(self) -> None:
        self.surface.close()

    def has_fixed_size(self) -> bool:
        hints = self.surface.size_hints
        # TODO: Maybe consider these flags too:
        # "PMinSize" in self.hints["flags"] and "PMaxSize" in self.hints["flags"]
        return bool(
            hints
            and 0 < hints.min_width == hints.max_width
            and 0 < hints.min_height == hints.max_height
        )

    def is_transient_for(self) -> base.WindowType | None:
        """What window is this window a transient window for?"""
        parent = self.surface.parent
        if parent:
            for win in self.qtile.windows_map.values():
                if isinstance(win, XWindow) and win.surface == parent:
                    return win
        return None

    def get_pid(self) -> int:
        return self.surface.pid

    def get_wm_type(self) -> str | None:
        wm_type = self.surface.window_type
        if wm_type:
            return self.core.xwayland_atoms[wm_type[0]]
        return None

    def get_wm_role(self) -> str | None:
        return self.surface.role

    def _update_fullscreen(self, do_full: bool) -> None:
        if do_full != (self._float_state == FloatStates.FULLSCREEN):
            self.surface.set_fullscreen(do_full)
            if self.ftm_handle:
                self.ftm_handle.set_fullscreen(do_full)

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
        # Adjust the placement to account for layout margins, if there are any.
        if margin is not None:
            if isinstance(margin, int):
                margin = [margin] * 4
            x += margin[3]
            y += margin[0]
            width -= margin[1] + margin[3]
            height -= margin[0] + margin[2]

        if respect_hints:
            hints = self.surface.size_hints
            if hints:
                width = max(width, hints.min_width)
                height = max(height, hints.min_height)
                if hints.max_width > 0:
                    width = min(width, hints.max_width)
                if hints.max_height > 0:
                    height = min(height, hints.max_height)

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self.float_x = x - self.group.screen.x
            self.float_y = y - self.group.screen.y

        self.x = x
        self.y = y
        self._width = width
        self._height = height
        self.container.node.set_position(x, y)
        self.surface.configure(x, y, width, height)
        self.paint_borders(bordercolor, borderwidth)

        if above:
            self.bring_to_front()

    @expose_command()
    def bring_to_front(self) -> None:
        self.surface.restack(None, 0)  # XCB_STACK_MODE_ABOVE
        self.container.node.raise_to_top()

    @expose_command()
    def static(
        self,
        screen: int | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        Window.static(self, screen, x, y, width, height)
        hook.fire("client_managed", self.qtile.windows_map[self._wid])

    def _to_static(self, x: int | None, y: int | None, width: int | None, height: int | None) -> XStatic:
        return XStatic(
            self.core, self.qtile, self, self._idle_inhibitors_count, x, y, width, height
        )


class XStatic(Static[xwayland.Surface]):
    """A static window belonging to the XWayland shell."""

    surface: xwayland.Surface

    def __init__(
        self,
        core: Core,
        qtile: Qtile,
        win: XWindow,
        idle_inhibitor_count: int,
        x: int | None,
        y: int | None,
        width: int | None,
        height: int | None,
    ):
        surface = win.surface
        Static.__init__(
            self, core, qtile, surface, win.wid, idle_inhibitor_count=idle_inhibitor_count
        )
        self._wm_class = surface.wm_class

        self.conf_x = x
        self.conf_y = y
        self.conf_width = width
        self.conf_height = height

        self.add_listener(surface.map_event, self._on_map)
        self.add_listener(surface.unmap_event, self._on_unmap)
        self.add_listener(surface.destroy_event, self._on_destroy)
        self.add_listener(surface.surface.commit_event, self._on_commit)
        self.add_listener(surface.request_configure_event, self._on_request_configure)
        self.add_listener(surface.set_title_event, self._on_set_title)
        self.add_listener(surface.set_class_event, self._on_set_class)

        # Checks to see if the user manually created the XStatic surface.
        # In which case override_redirect would be false.
        if surface.override_redirect:
            self.add_listener(surface.set_geometry_event, self._on_set_geometry)

        # While XWindows will always have a foreign toplevel handle, as they are always
        # regular windows, XStatic windows can be: 1) regular windows made static by the
        # user, which have a handle, or 2) XWayland popups (like OR windows), which
        # we won't give a handle.
        self.ftm_handle: ftm.ForeignToplevelHandleV1 | None = None

        # Take control of the scene node and tree
        self.container = win.container
        self.container.node.data = self.data_handle
        self.tree = win.tree

    def _on_unmap(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic unmap")
        # When an X static window unmaps, just finalize it completely, re-instantiate a
        # regular XWindow instance, and stick it into a pending state. This way, the
        # client can re-use the window with a new xwayland surface without issue. There
        # is certainly a nicer way to do this but that's a TODO.
        self._on_destroy(None, None)  # type: ignore
        win = XWindow(self.core, self.qtile, self.surface)
        self.core.pending_windows.add(win)

    def _on_commit(self, _listener: Listener, _data: Any) -> None:
        pass
        # logger.debug("Signal: xstatic commit")

    def _on_request_configure(self, _listener: Listener, event: SurfaceConfigureEvent) -> None:
        logger.debug("Signal: xstatic request_configure")
        cw = ConfigWindow
        if self.conf_x is None and event.mask & cw.X:
            self.x = event.x
        if self.conf_y is None and event.mask & cw.Y:
            self.y = event.y
        if self.conf_width is None and event.mask & cw.Width:
            self.width = event.width
        if self.conf_height is None and event.mask & cw.Height:
            self.height = event.height
        self.place(self.x, self.y, self.width, self.height, self.borderwidth, self.bordercolor)

    @expose_command()
    def kill(self) -> None:
        self.surface.close()

    def hide(self) -> None:
        super().hide()
        self.container.node.set_enabled(enabled=False)

    def unhide(self) -> None:
        if self not in self.core.pending_windows:
            # Only when mapping does the xwayland_surface have a wlr_surface that we can
            # listen for commits on and create a tree for.
            self.add_listener(self.surface.surface.commit_event, self._on_commit)
            if not self.tree:
                self.tree = SceneTree.subsurface_tree_create(self.container, self.surface.surface)
                self.tree.node.set_position(self.borderwidth, self.borderwidth)

            self.container.node.set_enabled(enabled=True)
            self.bring_to_front()
            return

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
        self.surface.configure(x, y, self._width, self._height)
        self.container.node.set_position(x, y)

    def _on_set_title(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic set_title")
        title = self.surface.title
        if title and title != self.name:
            self.name = title
            if self.ftm_handle:
                self.ftm_handle.set_title(title)
            hook.fire("client_name_updated", self)

    def _on_set_class(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic set_class")
        self._wm_class = self.surface.wm_class
        if self.ftm_handle:
            self.ftm_handle.set_app_id(self._wm_class or "")

    def _on_set_geometry(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: xstatic set_geometry")
        # check if the surface has moved
        if self.surface.x != self.x or self.surface.y != self.y:
            self.place(
                self.surface.x, self.surface.y, self.surface.width, self.surface.height, 0, None
            )

    @expose_command()
    def bring_to_front(self) -> None:
        self.surface.restack(None, 0)  # XCB_STACK_MODE_ABOVE
        self.container.node.raise_to_top()
