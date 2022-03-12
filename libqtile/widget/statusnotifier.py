# Copyright (c) 2021 elParaguayo
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

import asyncio
import os
from functools import partial

# dbus_next is incompatible with deferred type evaluation
from typing import Callable, List, Optional

import cairocffi
from dbus_next import InterfaceNotFoundError, InvalidBusNameError, InvalidObjectPathError
from dbus_next.aio import MessageBus
from dbus_next.constants import PropertyAccess
from dbus_next.errors import DBusError
from dbus_next.service import ServiceInterface, dbus_property, method, signal

try:
    from xdg.IconTheme import getIconPath

    has_xdg = True
except ImportError:
    has_xdg = False

from libqtile import bar
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.utils import add_signal_receiver
from libqtile.widget import base

# StatusNotifier seems to have two potential interface names.
# While KDE appears to be the default, we should also listen
# for items on freedesktop.
BUS_NAMES = ["org.kde.StatusNotifierWatcher", "org.freedesktop.StatusNotifierWatcher"]

ITEM_INTERFACES = ["org.kde.StatusNotifierItem", "org.freedesktop.StatusNotifierItem"]

STATUSNOTIFIER_PATH = "/StatusNotifierItem"
PROTOCOL_VERSION = 0


class StatusNotifierItem:  # noqa: E303
    """
    Class object which represents an StatusNotiferItem object.

    The item is responsible for interacting with the
    application.
    """

    icon_map = {
        "Icon": ("_icon", "get_icon_pixmap"),
        "Attention": ("_attention_icon", "get_attention_icon_pixmap"),
        "Overlay": ("_overlay_icon", "get_overlay_icon_pixmap"),
    }

    def __init__(self, bus, service, path=None, icon_theme=None):
        self.bus = bus
        self.service = service
        self.surfaces = {}
        self._pixmaps = {}
        self._icon = None
        self._overlay_icon = None
        self._attention_icon = None
        self.on_icon_changed = None
        self.icon_theme = icon_theme
        self.icon = None
        self.path = path if path else STATUSNOTIFIER_PATH

    def __eq__(self, other):
        # Convenience method to find Item in list by service path
        if isinstance(other, StatusNotifierItem):
            return other.service == self.service
        elif isinstance(other, str):
            return other == self.service
        else:
            return False

    async def start(self):
        # Create a proxy object connecting for the item.
        # Some apps provide the incorrect path to the StatusNotifier object
        # We can try falling back to the default if that fails.
        # See: https://github.com/qtile/qtile/issues/3418
        # Note: this loop will run a maximum of two times and returns False
        # if the no object is available.
        found_path = False

        while not found_path:
            try:
                introspection = await self.bus.introspect(self.service, self.path)
                found_path = True
            except InvalidObjectPathError:
                logger.info(f"Cannot find {self.path} path on {self.service}.")
                if self.path == STATUSNOTIFIER_PATH:
                    return False

                # Try the default ('/StatusNotifierItem')
                self.path = STATUSNOTIFIER_PATH

        try:
            obj = self.bus.get_proxy_object(self.service, self.path, introspection)
        except InvalidBusNameError:
            return False

        # Try to connect to the bus object and verify there's a valid
        # interface available
        # TODO: This may not ever fail given we've specified the underying
        # schema so dbus-next has not attempted any introspection.
        interface_found = False
        for interface in ITEM_INTERFACES:
            try:
                self.item = obj.get_interface(interface)
                interface_found = True
                break
            except InterfaceNotFoundError:
                continue

        if not interface_found:
            logger.warning(f"Unable to find StatusNotifierItem" f"interface on {self.service}")
            return False

        # Default to XDG icon:
        icon_name = await self.item.get_icon_name()

        try:
            icon_path = await self.item.get_icon_theme_path()
            self.icon = self._get_custom_icon(icon_name, icon_path)
        except (AttributeError, DBusError):
            pass

        if not self.icon:
            self.icon = self._get_xdg_icon(icon_name)

        # If there's no XDG icon, try to use icon provided by application
        if self.icon is None:

            # Get initial application icons:
            for icon in ["Icon", "Attention", "Overlay"]:
                await self._get_icon(icon)

            # Attach listeners for when the icon is updated
            self.item.on_new_icon(self._new_icon)
            self.item.on_new_attention_icon(self._new_attention_icon)
            self.item.on_new_overlay_icon(self._new_overlay_icon)

        if not self.has_icons:
            logger.warning(
                "Cannot find icon in current theme and " "no icon provided by StatusNotifierItem."
            )

        return True

    def _new_icon(self):
        task = asyncio.create_task(self._get_icon("Icon"))
        task.add_done_callback(self._redraw)

    def _new_attention_icon(self):
        task = asyncio.create_task(self._get_icon("Attention"))
        task.add_done_callback(self._redraw)

    def _new_overlay_icon(self):
        task = asyncio.create_task(self._get_icon("Overlay"))
        task.add_done_callback(self._redraw)

    def _get_custom_icon(self, icon_name, icon_path):
        for ext in [".png", ".svg"]:
            path = os.path.join(icon_path, icon_name + ext)
            if os.path.isfile(path):
                return Img.from_path(path)

        return None

    def _get_xdg_icon(self, icon_name):
        if not has_xdg:
            return

        path = getIconPath(icon_name, theme=self.icon_theme, extensions=["png", "svg"])

        if not path:
            return None

        return Img.from_path(path)

    async def _get_icon(self, icon_name):
        """
        Requests the pixmap for the given `icon_name` and
        adds to an internal dictionary for later retrieval.
        """
        attr, method = self.icon_map[icon_name]
        pixmap = getattr(self.item, method)
        icon_pixmap = await pixmap()

        # Items can present multiple pixmaps for different
        # size of icons. We want to keep these so we can pick
        # the best size when redering the icon later.
        # Also, the bytes sent for the pixmap are big-endian
        # but Cairo expects little-endian so we need to
        # reorder them.
        self._pixmaps[icon_name] = {
            size: self._reorder_bytes(icon_bytes) for size, _, icon_bytes in icon_pixmap
        }

    def _reorder_bytes(self, icon_bytes):
        """
        Method loops over the array and reverses every
        4 bytes (representing one RGBA pixel).
        """
        arr = bytearray(icon_bytes)
        for i in range(0, len(arr), 4):
            arr[i : i + 4] = arr[i : i + 4][::-1]

        return arr

    def _redraw(self, result):
        """Method to invalidate icon cache and redraw icons."""
        self._invalidate_icons()
        if self.on_icon_changed is not None:
            self.on_icon_changed()

    def _invalidate_icons(self):
        self.surfaces = {}

    def _get_sizes(self):
        """Returns list of available icon sizes."""
        if not self._pixmaps.get("Icon", False):
            return []

        return sorted([size for size in self._pixmaps["Icon"]])

    def _get_surfaces(self, size):
        """
        Creates a Cairo ImageSurface for each available icon
        for the given size.
        """
        raw_surfaces = {}
        for icon in self._pixmaps:
            if size in self._pixmaps[icon]:
                srf = cairocffi.ImageSurface.create_for_data(
                    self._pixmaps[icon][size], cairocffi.FORMAT_ARGB32, size, size
                )
                raw_surfaces[icon] = srf
        return raw_surfaces

    def get_icon(self, size):
        """
        Returns a cairo ImageSurface for the selected `size`.

        Will pick the appropriate icon and add any overlay as required.
        """
        # Use existing icon if generated previously
        if size in self.surfaces:
            return self.surfaces[size]

        # Create a blank ImageSurface to hold the icon
        icon = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, size, size)

        if self.icon:
            base_icon = self.icon.surface
            icon_size = base_icon.get_width()
            overlay = None

        else:
            # Find best matching icon size:
            # We get all available sizes and filter this list so it only shows
            # the icon sizes bigger than the requested size (we prefer to
            # shrink icons rather than scale them up)
            all_sizes = self._get_sizes()
            sizes = [s for s in all_sizes if s >= size]

            # TODO: This is messy. Shouldn't return blank icon
            # If there are no sizes at all (i.e. no icon) then we return empty
            # icon
            if not all_sizes:
                return icon

            # Choose the first available size. If there are none (i.e. we
            # request icon size bigger than the largest provided by the app),
            # we just take the largest icon
            icon_size = sizes[0] if sizes else all_sizes[-1]

            srfs = self._get_surfaces(icon_size)

            # TODO: This shouldn't happen...
            if not srfs:
                return icon

            # TODO: Check spec for when to use "attention"
            base_icon = srfs.get("Attention", srfs["Icon"])
            overlay = srfs.get("Overlay", None)

        with cairocffi.Context(icon) as ctx:
            scale = size / icon_size
            ctx.scale(scale, scale)
            ctx.set_source_surface(base_icon)
            ctx.paint()
            if overlay:
                ctx.set_source_surface(overlay)
                ctx.paint()

        # Store the surface for next time
        self.surfaces[size] = icon

        return icon

    def activate(self):
        asyncio.create_task(self._activate())

    async def _activate(self):
        # Call Activate method and pass window position hints
        await self.item.call_activate(0, 0)

    @property
    def has_icons(self):
        return any(bool(icon) for icon in self._pixmaps.values()) or self.icon is not None


class StatusNotifierWatcher(ServiceInterface):  # noqa: E303
    """
    DBus service that creates a StatusNotifierWatcher interface
    on the bus and listens for applications wanting to register
    items.
    """

    def __init__(self, service: str):
        super().__init__(service)
        self._items: List[str] = []
        self._hosts: List[str] = []
        self.service = service
        self.on_item_added: Optional[Callable] = None
        self.on_host_added: Optional[Callable] = None
        self.on_item_removed: Optional[Callable] = None
        self.on_host_removed: Optional[Callable] = None

    async def start(self):
        # Set up and register the service on ths bus
        self.bus = await MessageBus().connect()
        self.bus.add_message_handler(self._message_handler)
        self.bus.export("/StatusNotifierWatcher", self)
        await self.bus.request_name(self.service)

        # We need to listen for interfaces being removed from
        # the bus so we can remove icons when the application
        # is closed.
        await self._setup_listeners()

    def _message_handler(self, message):
        """
        Low level method to check incoming messages.

        Ayatana indicators seem to register themselves by passing their object
        path rather than the service providing that object. We therefore need
        to identify the sender of the message in order to register the service.

        Returning False so senders receieve a reply (returning True prevents
        reply being sent)
        """
        if message.member != "RegisterStatusNotifierItem":
            return False

        # If the argument passed to the method is the service name then we
        # don't need to do anything else.
        if message.sender == message.body[0]:
            return False

        if message.sender not in self._items:
            self._items.append(message.sender)
            if self.on_item_added is not None:
                self.on_item_added(message.sender, message.body[0])
            self.StatusNotifierItemRegistered(message.sender)
        return False

    async def _setup_listeners(self):
        """
        Register a MatchRule to receive signals when interfaces are added
        and removed from the bus.
        """
        await add_signal_receiver(
            self._name_owner_changed,
            session_bus=True,
            signal_name="NameOwnerChanged",
            dbus_interface="org.freedesktop.DBus",
        )

    def _name_owner_changed(self, message):
        # We need to track when an interface has been removed from the bus
        # We use the NameOwnerChanged signal and check if the new owner is
        # empty.
        name, _, new_owner = message.body

        # Check if one of our registered items or hosts has been removed.
        # If so, remove from our list and emit relevant signal
        if new_owner == "" and name in self._items:
            self._items.remove(name)
            self.StatusNotifierItemUnregistered(name)

        if new_owner == "" and name in self._hosts:
            self._hosts.remove(name)
            self.StatusNotifierHostUnregistered(name)

    @method()
    def RegisterStatusNotifierItem(self, service: "s"):  # type: ignore  # noqa: F821, N802
        if service not in self._items:
            self._items.append(service)
            if self.on_item_added is not None:
                self.on_item_added(service)
            self.StatusNotifierItemRegistered(service)

    @method()
    def RegisterStatusNotifierHost(self, service: "s"):  # type: ignore  # noqa: F821, N802
        if service not in self._hosts:
            self._hosts.append(service)
            self.StatusNotifierHostRegistered(service)

    @dbus_property(access=PropertyAccess.READ)
    def RegisteredStatusNotifierItems(self) -> "as":  # type: ignore  # noqa: F722, F821, N802
        return self._items

    @dbus_property(access=PropertyAccess.READ)
    def IsStatusNotifierHostRegistered(self) -> "b":  # type: ignore  # noqa: F821, N802
        # Note: applications may not register items unless this
        # returns True
        return len(self._hosts) > 0

    @dbus_property(access=PropertyAccess.READ)
    def ProtocolVersion(self) -> "i":  # type: ignore  # noqa: F821, N802
        return PROTOCOL_VERSION

    @signal()
    def StatusNotifierItemRegistered(self, service) -> "s":  # type: ignore  # noqa: F821, N802
        return service

    @signal()
    def StatusNotifierItemUnregistered(self, service) -> "s":  # type: ignore  # noqa: F821, N802
        if self.on_item_removed is not None:
            self.on_item_removed(service)
        return service

    @signal()
    def StatusNotifierHostRegistered(self, service) -> "s":  # type: ignore  # noqa: F821, N802
        if self.on_host_added is not None:
            self.on_host_added(service)
        return service

    @signal()
    def StatusNotifierHostUnregistered(self, service) -> "s":  # type: ignore  # noqa: F821, N802
        if self.on_host_removed is not None:
            self.on_host_removed(service)
        return service


class StatusNotifierHost:  # noqa: E303
    """
    Host object to act as a bridge between the widget and the DBus objects.

    The Host collates items returned from multiple watcher interfaces and
    collates them into a single list for the widget to access.
    """

    def __init__(self):
        self.watchers: List[StatusNotifierWatcher] = []
        self.items: List[StatusNotifierItem] = []
        self.name = "qtile"
        self.icon_theme: str = None

    async def start(
        self,
        on_item_added: Optional[Callable] = None,
        on_item_removed: Optional[Callable] = None,
        on_icon_changed: Optional[Callable] = None,
    ):
        self.bus = await MessageBus().connect()
        self.on_item_added = on_item_added
        self.on_item_removed = on_item_removed
        self.on_icon_changed = on_icon_changed
        for iface in BUS_NAMES:
            w = StatusNotifierWatcher(iface)
            w.on_item_added = self.add_item
            w.on_item_removed = self.remove_item
            await w.start()

            # Not quite following spec here as we're not registering
            # the host on the bus.
            w.RegisterStatusNotifierHost(self.name)
            self.watchers.append(w)

    def item_added(self, item, service, future):
        success = future.result()
        # If StatusNotifierItem object was created successfully then we
        # add to our list and redraw the bar
        if success:
            self.items.append(item)
            if self.on_item_added:
                self.on_item_added(item)

    def add_item(self, service, path=None):
        """
        Creates a StatusNotifierItem for the given service and tries to
        start it.
        """
        item = StatusNotifierItem(self.bus, service, path=path, icon_theme=self.icon_theme)
        item.on_icon_changed = self.on_icon_changed
        if item not in self.items:
            task = asyncio.create_task(item.start())
            task.add_done_callback(partial(self.item_added, item, service))

    def remove_item(self, interface):
        # Check if the interface is in out list of items and, if so,
        # remove it and redraw the bar
        if interface in self.items:
            self.items.remove(interface)
            if self.on_item_removed:
                self.on_item_removed(interface)


host = StatusNotifierHost()  # noqa: E303


class StatusNotifier(base._Widget):
    """
    A 'system tray' widget using the freedesktop StatusNotifierItem
    specification.

    As per the specification, app icons are first retrieved from the
    user's current theme. If this is not available then the app may
    provide its own icon. In order to use this functionality, users
    are recommended to install the `xdg`_ module to support retrieving
    icons from the selected theme.

    Letf-clicking an icon will trigger an activate event.

    .. note::

        Context menus are not currently supported by the official widget.
        However, a modded version of the widget which provides basic menu
        support is available from elParaguayo's `qtile-extras
        <https://github.com/elParaguayo/qtile-extras>`_ repo.

    .. _xdg: https://pypi.org/project/xdg/
    """

    orientations = base.ORIENTATION_BOTH

    defaults = [
        ("icon_size", 16, "Icon width"),
        ("icon_theme", None, "Name of theme to use for app icons"),
        ("padding", 3, "Padding between icons"),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(StatusNotifier.defaults)
        self.add_callbacks(
            {
                "Button1": self.activate,
            }
        )
        self.selected_item: Optional[StatusNotifierItem] = None

    @property
    def available_icons(self):
        return [item for item in host.items if item.has_icons]

    def calculate_length(self):
        if not host.items:
            return 0

        return len(self.available_icons) * (self.icon_size + self.padding) + self.padding

    def _configure(self, qtile, bar):
        if has_xdg and self.icon_theme:
            host.icon_theme = self.icon_theme

        # This is called last as it starts timers including _config_async.
        base._Widget._configure(self, qtile, bar)

    async def _config_async(self):
        def draw(x=None):
            self.bar.draw()

        await host.start(on_item_added=draw, on_item_removed=draw, on_icon_changed=draw)

    def find_icon_at_pos(self, x, y):
        """returns StatusNotifierItem object for icon in given position"""
        offset = self.padding
        val = x if self.bar.horizontal else y

        if val < offset:
            return None

        for icon in self.available_icons:
            offset += self.icon_size
            if val < offset:
                return icon
            offset += self.padding

        return None

    def button_press(self, x, y, button):
        icon = self.find_icon_at_pos(x, y)
        self.selected_item = icon if icon else None

        name = "Button{0}".format(button)
        if name in self.mouse_callbacks:
            self.mouse_callbacks[name]()

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        if self.bar.horizontal:
            xoffset = self.padding
            yoffset = (self.bar.height - self.icon_size) // 2

            for item in self.available_icons:
                icon = item.get_icon(self.icon_size)
                self.drawer.ctx.set_source_surface(icon, xoffset, yoffset)
                self.drawer.ctx.paint()

                xoffset += self.icon_size + self.padding

            self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

        else:
            xoffset = (self.bar.width - self.icon_size) // 2
            yoffset = self.padding

            for item in self.available_icons:
                icon = item.get_icon(self.icon_size)
                self.drawer.ctx.set_source_surface(icon, xoffset, yoffset)
                self.drawer.ctx.paint()

                yoffset += self.icon_size + self.padding

            self.drawer.draw(offsety=self.offset, offsetx=self.offsetx, height=self.length)

    def activate(self):
        """Primary action when clicking on an icon"""
        if not self.selected_item:
            return
        self.selected_item.activate()
