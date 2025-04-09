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
from asyncio import current_task
from collections.abc import Callable
from contextlib import suppress
from functools import partial
from pathlib import Path

# dbus_fast is incompatible with deferred type evaluation
import cairocffi
from dbus_fast import InterfaceNotFoundError, InvalidBusNameError, InvalidObjectPathError
from dbus_fast.aio import MessageBus
from dbus_fast.constants import PropertyAccess
from dbus_fast.errors import DBusError
from dbus_fast.service import ServiceInterface, dbus_property, method, signal

try:
    from xdg.IconTheme import getIconPath

    has_xdg = True
except ImportError:
    has_xdg = False

from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.utils import add_signal_receiver, create_task

ICON_FORMATS = [".png", ".svg"]

# StatusNotifier seems to have two potential interface names.
# While KDE appears to be the default, we should also listen
# for items on freedesktop.
BUS_NAMES = ["org.kde.StatusNotifierWatcher", "org.freedesktop.StatusNotifierWatcher"]

ITEM_INTERFACES = ["org.kde.StatusNotifierItem", "org.freedesktop.StatusNotifierItem"]

STATUSNOTIFIER_PATH = "/StatusNotifierItem"
PROTOCOL_VERSION = 0

STATUS_NOTIFIER_ITEM_SPEC = """
<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
"http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name='org.kde.StatusNotifierItem'>
    <annotation name="org.gtk.GDBus.C.Name" value="Item" />
    <method name='ContextMenu'>
      <arg type='i' direction='in' name='x'/>
      <arg type='i' direction='in' name='y'/>
    </method>
    <method name='Activate'>
      <arg type='i' direction='in' name='x'/>
      <arg type='i' direction='in' name='y'/>
    </method>
    <method name='SecondaryActivate'>
      <arg type='i' direction='in' name='x'/>
      <arg type='i' direction='in' name='y'/>
    </method>
    <method name='Scroll'>
      <arg type='i' direction='in' name='delta'/>
      <arg type='s' direction='in' name='orientation'/>
    </method>
    <signal name='NewTitle'/>
    <signal name='NewIcon'/>
    <signal name='NewAttentionIcon'/>
    <signal name='NewOverlayIcon'/>
    <signal name='NewToolTip'/>
    <signal name='NewStatus'>
      <arg type='s' name='status'/>
    </signal>
    <property name='Category' type='s' access='read'/>
    <property name='Id' type='s' access='read'/>
    <property name='Title' type='s' access='read'/>
    <property name='Status' type='s' access='read'/>
    <!-- See discussion on pull #536
    <property name='WindowId' type='u' access='read'/>
    -->
    <property name='IconThemePath' type='s' access='read'/>
    <property name='IconName' type='s' access='read'/>
    <property name='IconPixmap' type='a(iiay)' access='read'/>
    <property name='OverlayIconName' type='s' access='read'/>
    <property name='OverlayIconPixmap' type='a(iiay)' access='read'/>
    <property name='AttentionIconName' type='s' access='read'/>
    <property name='AttentionIconPixmap' type='a(iiay)' access='read'/>
    <property name='AttentionMovieName' type='s' access='read'/>
    <property name='ToolTip' type='(sa(iiay)ss)' access='read'/>
    <property name='Menu' type='o' access='read'/>
    <property name='ItemIsMenu' type='b' access='read'/>
  </interface>
</node>
"""


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
        self.last_icon_name = None

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
            except InvalidBusNameError:
                # This is probably an Ayatana indicator which doesn't provide the service name.
                # We'll pick it up via the message handler so we can ignore this.
                return False
            except InvalidObjectPathError:
                logger.info("Cannot find %s path on %s.", self.path, self.service)
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
        # schema so dbus-fast has not attempted any introspection.
        interface_found = False
        for interface in ITEM_INTERFACES:
            try:
                self.item = obj.get_interface(interface)
                interface_found = True
                break
            except InterfaceNotFoundError:
                continue

        if not interface_found:
            logger.info(
                "Unable to find StatusNotifierItem interface on %s. Falling back to default spec.",
                self.service,
            )
            try:
                obj = self.bus.get_proxy_object(
                    self.service, STATUSNOTIFIER_PATH, STATUS_NOTIFIER_ITEM_SPEC
                )
                self.item = obj.get_interface("org.kde.StatusNotifierItem")
            except InterfaceNotFoundError:
                logger.warning(
                    "Failed to find StatusNotifierItem interface on %s and fallback to default spec also failed.",
                    self.service,
                )
                return False

        # Trying to get the local icon (first without fallback because there might be application-provided icons)
        await self._get_local_icon(fallback=False)

        # If there's no XDG icon, try to use icon provided by application
        if self.icon:
            self.item.on_new_icon(self._update_local_icon)
        else:
            # Get initial application icons:
            for icon in ["Icon", "Attention", "Overlay"]:
                await self._get_icon(icon)

            if self.has_icons:
                # Attach listeners for when the icon is updated
                self.item.on_new_icon(self._new_icon)
                self.item.on_new_attention_icon(self._new_attention_icon)
                self.item.on_new_overlay_icon(self._new_overlay_icon)

        if not self.has_icons:
            logger.warning(
                "Cannot find icon in current theme and no icon provided by StatusNotifierItem."
            )
            # No "local" icon and no application-provided icons are available.
            # The "local" icon may be updated at a later time, so "_update_local_icon"
            # gets registered for "on_new_icon" with the option to fall back to
            # a default icon.
            self.item.on_new_icon(self._update_local_icon)
            await self._get_local_icon()

        return True

    async def _get_local_icon(self, fallback=True):
        # Default to XDG icon
        # Some implementations don't provide an IconName property so we
        # need to catch an error if we can't read it.
        # We can't use hasattr to check this as the method will be created
        # where we've used the default XML spec to provide the object introspection
        icon_name = ""
        try:
            icon_name = await self.item.get_icon_name()
        except DBusError:
            return

        # We only need to do these searches if there's an icon name provided by
        # the app. We also don't want to do the recursive lookup with an empty
        # icon name as, otherwise, the glob will match things that are not images.
        if icon_name:
            if icon_name == self.last_icon_name:
                current_task().remove_done_callback(self._redraw)
                return

            self.last_icon_name = icon_name
            self.icon = None

            try:
                icon_path = await self.item.get_icon_theme_path()
            except (AttributeError, DBusError):
                icon_path = None

            icon = None
            if icon_path:
                icon = self._get_custom_icon(icon_name, Path(icon_path))

            if icon:
                self.icon = icon
            else:
                self.icon = self._get_xdg_icon(icon_name)
        else:
            self.icon = None

        if fallback:
            for icon in ["Icon", "Attention", "Overlay"]:
                await self._get_icon(icon)

        if not self.has_icons and fallback:
            # Use fallback icon libqtile/resources/status_notifier/fallback_icon.png
            logger.warning("Could not find icon for '%s'. Using fallback icon.", icon_name)
            path = Path(__file__).parent / "fallback_icon.png"
            self.icon = Img.from_path(path.resolve().as_posix())

    def _create_task_and_draw(self, coro):
        task = create_task(coro)
        task.add_done_callback(self._redraw)

    def _update_local_icon(self):
        self._create_task_and_draw(self._get_local_icon())

    def _new_icon(self):
        self._create_task_and_draw(self._get_icon("Icon"))

    def _new_attention_icon(self):
        self._create_task_and_draw(self._get_icon("Attention"))

    def _new_overlay_icon(self):
        self._create_task_and_draw(self._get_icon("Overlay"))

    def _get_custom_icon(self, icon_name, icon_path):
        icon = None
        for ext in ICON_FORMATS:
            path = icon_path / f"{icon_name}{ext}"
            if path.is_file():
                icon = path
                break

        else:
            # No icon found at the image path, let's search recursively
            glob = icon_path.rglob(f"{icon_name}.*")
            found = [
                icon for icon in glob if icon.is_file() and icon.suffix.lower() in ICON_FORMATS
            ]

            # Found a matching icon in subfolder
            if found:
                # We'd prefer an svg file
                svg = [icon for icon in found if icon.suffix.lower() == ".svg"]
                if svg:
                    icon = svg[0]
                else:
                    # If not, we'll take what there is
                    # NOTE: not clear how we can handle multiple matches with different icon sizes 16x16, 32x32 etc
                    icon = found[0]

        if icon is not None:
            return Img.from_path(icon.resolve().as_posix())

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
        pixmap = getattr(self.item, method, None)
        if pixmap is None:
            return
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
            self.on_icon_changed(self)

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
        if hasattr(self.item, "call_activate"):
            create_task(self._activate())

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
        self._items: list[str] = []
        self._hosts: list[str] = []
        self.service = service
        self.on_item_added: Callable | None = None
        self.on_host_added: Callable | None = None
        self.on_item_removed: Callable | None = None
        self.on_host_removed: Callable | None = None

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

        # If the argument is not an object path (starting with "/") then we assume
        # it is the bus name and we don't need to do anything else.
        if not message.body[0].startswith("/"):
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
            use_bus=self.bus,
            preserve=True,
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
        self.watchers: list[StatusNotifierWatcher] = []
        self.items: list[StatusNotifierItem] = []
        self.name = "qtile"
        self.icon_theme: str = None
        self.started = False
        self._on_item_added: list[Callable] = []
        self._on_item_removed: list[Callable] = []
        self._on_icon_changed: list[Callable] = []

    async def start(
        self,
        on_item_added: Callable | None = None,
        on_item_removed: Callable | None = None,
        on_icon_changed: Callable | None = None,
    ):
        """
        Starts the host if not already started.

        Widgets should register their callbacks via this method.
        """
        if on_item_added:
            self._on_item_added.append(on_item_added)

        if on_item_removed:
            self._on_item_removed.append(on_item_removed)

        if on_icon_changed:
            self._on_icon_changed.append(on_icon_changed)

        if self.started:
            if on_item_added:
                for item in self.items:
                    on_item_added(item)

        else:
            self.bus = await MessageBus().connect()
            await self.bus.request_name("org.freedesktop.StatusNotifierHost-qtile")
            for iface in BUS_NAMES:
                w = StatusNotifierWatcher(iface)
                w.on_item_added = self.add_item
                w.on_item_removed = self.remove_item
                await w.start()

                # Not quite following spec here as we're not registering
                # the host on the bus.
                w.RegisterStatusNotifierHost(self.name)
                self.watchers.append(w)
            self.started = True

    def item_added(self, item, service, future):
        success = future.result()
        # If StatusNotifierItem object was created successfully then we
        # add to our list and redraw the bar
        if success:
            self.items.append(item)
            for callback in self._on_item_added:
                callback(item)

        # It's an invalid item so let's remove it from the watchers
        else:
            for w in self.watchers:
                try:
                    w._items.remove(service)
                except ValueError:
                    pass

    def add_item(self, service, path=None):
        """
        Creates a StatusNotifierItem for the given service and tries to
        start it.
        """
        item = StatusNotifierItem(self.bus, service, path=path, icon_theme=self.icon_theme)
        item.on_icon_changed = self.item_icon_changed
        if item not in self.items:
            task = create_task(item.start())
            task.add_done_callback(partial(self.item_added, item, service))

    def remove_item(self, interface):
        # Check if the interface is in out list of items and, if so,
        # remove it and redraw the bar
        if interface in self.items:
            self.items.remove(interface)
            for callback in self._on_item_removed:
                callback(interface)

    def item_icon_changed(self, item):
        for callback in self._on_icon_changed:
            callback(item)

    def unregister_callbacks(
        self, on_item_added=None, on_item_removed=None, on_icon_changed=None
    ):
        if on_item_added is not None:
            with suppress(ValueError):
                self._on_item_added.remove(on_item_added)

        if on_item_removed is not None:
            with suppress(ValueError):
                self._on_item_removed.remove(on_item_removed)

        if on_icon_changed is not None:
            with suppress(ValueError):
                self._on_icon_changed.remove(on_icon_changed)


host = StatusNotifierHost()  # noqa: E303
