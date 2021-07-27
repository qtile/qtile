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
import time
from functools import partial
from typing import Callable, List, Optional

import cairocffi
from dbus_next import (
    InterfaceNotFoundError,
    InvalidBusNameError,
    InvalidIntrospectionError,
    Variant,
)
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
from libqtile.popup.menu import PopupMenu
from libqtile.resources.status_notifier import (
    SCHEMA_DBUS_MENU,
    SCHEMA_STATUS_NOTIFIER_ITEM,
)
from libqtile.utils import add_signal_receiver
from libqtile.widget import base

# StatusNotifier seems to have two potential interface names.
# While KDE appears to be the default, we should also listen
# for items on freedesktop.
BUS_NAMES = [
    'org.kde.StatusNotifierWatcher',
    'org.freedesktop.StatusNotifierWatcher'
]

ITEM_INTERFACES = [
    'org.kde.StatusNotifierItem',
    'org.freedesktop.StatusNotifierItem'
]

STATUSNOTIFIER_PATH = '/StatusNotifierItem'
PROTOCOL_VERSION = 0

MENU_INTERFACE = "com.canonical.dbusmenu"
NO_MENU = "/NO_DBUSMENU"


class DBusMenuItem:  # noqa: E303
    """Simple class definition to represent a DBus Menu item."""
    def __init__(self, menu, id: int, item_type: Optional[str] = "",
                 enabled: Optional[bool] = True, visible: Optional[bool] = True,
                 icon_name: Optional[str] = "", icon_data: Optional[List[bytes]] = list(),
                 shortcut: Optional[List[List[str]]] = list(), label: Optional[str] = "",
                 toggle_type: Optional[str] = "", toggle_state: Optional[int] = 0,
                 children_display: Optional[str] = ""):
        self.menu = menu
        self.id = id
        self.item_type = item_type
        self.enabled = enabled
        self.visible = visible
        self.icon_name = icon_name
        self.icon_data = icon_data
        self.shortcut = shortcut
        self.toggle_type = toggle_type
        self.toggle_state = toggle_state
        self.children_display = children_display
        self.label = label

    # TODO: Need a method to update properties based on a "PropertiesChanged" event

    def __repr__(self):
        """Custom repr to help debugging."""
        txt = f"'{self.label.replace('_','')}'" if self.label else self.item_type
        if self.children_display == "submenu":
            txt += "*"
        return f"<DBusMenuItem ({self.id}:{txt})>"

    def click(self):
        if self.children_display == "submenu":
            self.menu.parent.get_menu(self.id)
        else:
            asyncio.create_task(self.menu.click(self.id))


class DBusMenu:  # noqa: E303
    """
    Class object to connect DBusMenu interface and and interact with applications.
    """
    MENU_UPDATED = 0
    MENU_USE_STORED = 1
    MENU_NOT_FOUND = 2

    item_key_map = [
        ("type", "item_type"),
        ("icon-name", "icon_name"),
        ("icon-data", "icon_data"),
        ("toggle-state", "toggle_state"),
        ("children-display", "children_display"),
        ("toggle-type", "toggle_type")
    ]

    def __init__(self, parent, service: str, path: str, bus: Optional[MessageBus] = None):
        self.parent = parent
        self.service = service
        self.path = path
        self.bus = bus
        self._menus = {}

    async def start(self):
        """
        Connect to session bus and create object representing menu interface.
        """
        if self.bus is None:
            self.bus = await MessageBus().connect()

        try:
            self._bus_object = self.bus.get_proxy_object(
                self.service,
                self.path,
                SCHEMA_DBUS_MENU
            )

            self._interface = self._bus_object.get_interface(
                MENU_INTERFACE
            )

            # Menus work by giving each menu item an ID and actions are
            # toggled by sending this ID back to the application. These
            # IDs are updated regularly so we subscribe to a signal to make
            # we can keep the menu up to date.
            self._interface.on_layout_updated(self._layout_updated)

            return True

        # Catch errors which indicate a failure to connect to the menu interface.
        except InterfaceNotFoundError:
            logger.warning(f"Cannot find {self.iface} interface")
            return False
        except (DBusError, InvalidIntrospectionError):
            logger.warning(f"Path {self.path} does not present a valid dbusmenu object")
            return False

    def _layout_updated(self, revision, parent):
        """
        Checks whether we have already requested this menu and, if so, check if
        the revision number is less than the updated one.
        The updated menu is not requested at this point as it could be invalidated
        again before it is required.
        """
        if parent in self._menus and self._menus[parent]["revision"] < revision:
            del self._menus[parent]

    async def _get_menu(self, root):
        """
        Method to retrieve the menu layout from the DBus interface.
        """
        # Alert the app that we're about to draw a menu
        # Returns a boolean confirming whether menu should be refreshed
        try:
            needs_update = await self._interface.call_about_to_show(root)
        except DBusError:
            # Catch scenario where menu may be unavailable
            self.menu = None
            return self.MENU_NOT_FOUND, None

        # Check if the menu needs updating or if we've never drawn it before
        if needs_update or root not in self._menus:

            menu = await self._interface.call_get_layout(
                root,       # ParentID
                1,          # Recursion depth
                [],         # Property names (empty = all)
            )

            return self.MENU_UPDATED, menu

        return self.MENU_USE_STORED, None

    # TODO: Probably a better way of dealing with this...
    def _fix_menu_keys(self, item):
        for old, new in self.item_key_map:
            if old in item:
                item[new] = item.pop(old)

        for key in item:
            item[key] = item[key].value

        return item

    def get_menu(self, callback: Callable, root: int = 0):
        """
        Method called by widget to request the menu.
        Callback needs to accept a list of DBusMenuItems.
        """
        task = asyncio.create_task(self._get_menu(root))
        task.add_done_callback(
            partial(self.parse_menu, root, callback)
        )
        return

    def parse_menu(self, root, callback, task):
        update_needed, returned_menu = task.result()

        if update_needed == self.MENU_UPDATED:

            # Remember the menu revision ID so we know whether to update or not
            revision, layout = returned_menu

            # Menu is array of id, dict confirming there is a submenu
            # (the submenu is the main menu) and the menu items.
            _, _, menuitems = layout

            menu = []

            for item in menuitems:
                # Each item is a list of item ID, dictionary of item properties
                # and a list for submenus
                id, menudict, _ = item.value

                menu_item = DBusMenuItem(
                    self,
                    id,
                    **self._fix_menu_keys(menudict)
                )
                menu.append(menu_item)

            # Store this menu in case we need to draw it again
            self._menus[root] = {
                "revision": revision,
                "menu": menu
            }
        elif update_needed == self.MENU_USE_STORED:
            menu = self._menus[root]["menu"]

        # Send menu to the callback
        callback(menu)

    async def click(self, id):
        """Sends "clicked" event for the given item to the application."""
        await self._interface.call_event(
            id,  # ID of clicked menu item
            "clicked",  # Event type
            Variant("s", ""),  # "Data"
            int(time.time())  # Timestamp
        )

        # Ugly hack: delete all stored menus if the menu has been clicked
        # This will force a reload when the menu is next generated.
        self._menus = {}


class StatusNotifierItem:  # noqa: E303
    """
    Class object which represents an StatusNotiferItem object.

    The item contains information about both the icon and the
    attached menu.

    The item is also responsible for interacting with the
    application.
    """
    icon_map = {
        "Icon": ("_icon", "get_icon_pixmap"),
        "Attention": ("_attention_icon", "get_attention_icon_pixmap"),
        "Overlay": ("_overlay_icon", "get_overlay_icon_pixmap")
    }

    def __init__(self, bus, service, path=None,
                 display_menu_callback=None,
                 icon_theme=None):
        self.bus = bus
        self.service = service
        self.surfaces = {}
        self._pixmaps = {}
        self._icon = None
        self._overlay_icon = None
        self._attention_icon = None
        self.on_icon_changed = None
        self.is_context_menu = False
        self.display_menu_callback = display_menu_callback
        self.icon_theme = icon_theme
        self.menu = None
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
        if self.path == STATUSNOTIFIER_PATH:
            introspection = SCHEMA_STATUS_NOTIFIER_ITEM
        else:
            introspection = await self.bus.introspect(
                self.service,
                self.path
            )

        try:
            obj = self.bus.get_proxy_object(
                self.service,
                self.path,
                introspection
            )
        except InvalidBusNameError:
            return False

        # Try to connect to the bus object and verify there's a valid
        # interface available
        # TODO: This may not ever fail given we've specified the underying schema
        # so dbus-next has not attempted any introspection.
        interface_found = False
        for interface in ITEM_INTERFACES:
            try:
                self.item = obj.get_interface(interface)
                interface_found = True
                break
            except InterfaceNotFoundError:
                continue

        if not interface_found:
            logger.warning(f"Unable to find StatusNotifierItem interface on {self.service}")
            return False

        # Check if the default action for this item should be to show a context menu
        try:
            self.is_context_menu = await self.item.get_item_is_menu()
        except AttributeError:
            self.is_context_menu = False

        # Get the path of the attached menu
        menu_path = await self.item.get_menu()

        # If there is a menu then create and start the menu object
        if menu_path and menu_path != NO_MENU:
            self.menu = DBusMenu(self, self.service, menu_path, self.bus)
            await self.menu.start()

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
            logger.warning("Cannot find icon in current theme and no icon provided by StatusNotifierItem.")

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

        path = getIconPath(icon_name, theme=self.icon_theme,
                           extensions=['png', 'svg'])

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
            size: self._reorder_bytes(icon_bytes)
            for size, _, icon_bytes in icon_pixmap
        }

    def _reorder_bytes(self, icon_bytes):
        """
        Method loops over the array and reverses every
        4 bytes (representing one RGBA pixel).
        """
        arr = bytearray(icon_bytes)
        for i in range(0, len(arr), 4):
            arr[i:i+4] = arr[i:i+4][::-1]

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
                    self._pixmaps[icon][size],
                    cairocffi.FORMAT_ARGB32,
                    size,
                    size
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
        icon = cairocffi.ImageSurface(
            cairocffi.FORMAT_ARGB32,
            size,
            size
        )

        if self.icon:
            base_icon = self.icon.surface
            icon_size = base_icon.get_width()
            overlay = None

        else:
            # Find best matching icon size:
            # We get all available sizes and filter this list so it only shows
            # the icon sizes bigger than the requested size (we prefer to shrink
            # icons rather than scale them up)
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

    def get_menu(self, root: int = 0):
        if self.menu:
            self.menu.get_menu(self.display_menu_callback, root)

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
        self._items = []
        self._hosts = []
        self.service = service
        self.on_item_added = None
        self.on_host_added = None
        self.on_item_removed = None
        self.on_host_removed = None

    async def start(self):
        # Set up and register the service on ths bus
        self.bus = await MessageBus().connect()
        self.bus.add_message_handler(self._message_handler)
        self.bus.export('/StatusNotifierWatcher', self)
        await self.bus.request_name(self.service)

        # We need to listen for interfaces being removed from
        # the bus so we can remove icons when the application
        # is closed.
        await self._setup_listeners()

    def _message_handler(self, message):
        """
        Low level method to check incoming messages.

        Ayatana indicators seem to register themselves by passing their object
        path rather than the service providing that object. We therefore need to
        identify the sender of the message in order to register the service.
        """
        if message.member != "RegisterStatusNotifierItem":
            return False

        # If the argument passed to the method is the service name then we
        # don't need to do anything else.
        if message.sender == message.body[0]:
            return False

        self._items.append(message.sender)
        self.on_item_added(message.sender, message.body[0])
        return True

    async def _setup_listeners(self):
        """
        Register a MatchRule to receive signals when interfaces are added
        and removed from the bus.
        """
        await add_signal_receiver(
            self._name_owner_changed,
            session_bus=True,
            signal_name="NameOwnerChanged",
            dbus_interface="org.freedesktop.DBus"
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
    def RegisterStatusNotifierItem(self, service: 's'):  # noqa: F821
        if service not in self._items:
            self._items.append(service)
            self.StatusNotifierItemRegistered(service)

    @method()
    def RegisterStatusNotifierHost(self, service: 's'):  # noqa: F821
        if service not in self._hosts:
            self._hosts.append(service)
            self.StatusNotifierHostRegistered(service)

    @dbus_property(access=PropertyAccess.READ)
    def RegisteredStatusNotifierItems(self) -> 'as':  # noqa: F722, F821
        return self._items

    @dbus_property(access=PropertyAccess.READ)
    def IsStatusNotifierHostRegistered(self) -> 'b':  # noqa: F821
        # Note: applications may not register items unless this
        # returns True
        return len(self._hosts) > 0

    @dbus_property(access=PropertyAccess.READ)
    def ProtocolVersion(self) -> 'i':  # noqa: F821
        return PROTOCOL_VERSION

    @signal()
    def StatusNotifierItemRegistered(self, service) -> 's':  # noqa: F821
        if self.on_item_added is not None:
            self.on_item_added(service)
        return service

    @signal()
    def StatusNotifierItemUnregistered(self, service) -> 's':  # noqa: F821
        if self.on_item_removed is not None:
            self.on_item_removed(service)
        return service

    @signal()
    def StatusNotifierHostRegistered(self, service) -> 's':  # noqa: F821
        if self.on_host_added is not None:
            self.on_host_added(service)
        return service

    @signal()
    def StatusNotifierHostUnregistered(self, service) -> 's':  # noqa: F821
        if self.on_host_removed is not None:
            self.on_host_removed(service)
        return service


class StatusNotifierHost:  # noqa: E303
    """
    Host object to act as a bridge between the widget and the DBus objects.

    The Host collates items returned from multiple watcher interfaces and collates
    them into a single list for the widget to access.
    """
    def __init__(self):
        self.watchers: List[StatusNotifierWatcher] = []
        self.items: List[StatusNotifierItem] = []
        self.name = "qtile"
        self.display_menu_callback = None
        self.icon_theme = None

    async def start(self, widget):
        self.widget = widget
        self.bus = await MessageBus().connect()
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
            self.widget.bar.draw()

    def add_item(self, service, path=None):
        """
        Creates a StatusNotifierItem for the given service and tries to
        start it.
        """
        item = StatusNotifierItem(self.bus, service,
                                  path=path,
                                  display_menu_callback=self.display_menu_callback,
                                  icon_theme=self.icon_theme)
        item.on_icon_changed = self.widget.bar.draw
        if item not in self.items:
            task = asyncio.create_task(item.start())
            task.add_done_callback(
                partial(self.item_added, item, service)
            )

    def remove_item(self, interface):
        # Check if the interface is in out list of items and, if so,
        # remove it and redraw the bar
        if interface in self.items:
            self.items.remove(interface)
            self.widget.bar.draw()


host = StatusNotifierHost()  # noqa: E303


class StatusNotifier(base._Widget):
    """
    A 'system tray' widget using the freedesktop StatusNotifierItem specification.

    Letf-clicking an icon will trigger an activate event.
    Right-clicking an icon will display a context menu where provided by the application.
    """

    orientations = base.ORIENTATION_BOTH

    defaults = [
        ('icon_size', 16, 'Icon width'),
        ('icon_theme', None, 'Name of theme to use for app icons'),
        ('padding', 5, 'Padding between icons'),
        ('font', 'sans', 'Font for menu text'),
        ('fontsize', 12, 'Font size for menu text'),
        ('foreground', 'ffffff', 'Font colour for menu text'),
        ('menu_background', '333333', 'Background colour for menu'),
        ('separator_colour', '555555', 'Colour of menu separator'),
        ('highlight_colour', '0060A0', 'Colour of highlight for menu items (None for no highlight)'),
        (
            'menu_row_height',
            None,
            (
                'Height of menu row (NB text entries are 2 rows tall, separators are 1 row tall.) '
                '"None" will attempt to calculate height based on font size.'
            )
        ),
        ('menu_width', 200, 'Context menu width'),
        ('show_menu_icons', True, 'Show icons in context menu'),
        ('hide_after', 0.5, 'Time in seconds before hiding menu atfer mouse leave'),
        ('opacity', 1, 'Menu opactity')
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(StatusNotifier.defaults)
        self.add_callbacks(
            {
                "Button1": self.activate,
                "Button3": self.show_menu
            }
        )

        self.menu_config = {
            'background': self.menu_background,
            'font': self.font,
            'fontsize': self.fontsize,
            'foreground': self.foreground,
            'highlight': self.highlight_colour,
            'show_menu_icons': self.show_menu_icons,
            'hide_after': self.hide_after,
            'colour_above': self.separator_colour,
            'opacity': self.opacity,
            'row_height': self.menu_row_height,
            'menu_width': self.menu_width
        }

    @property
    def available_icons(self):
        return [item for item in self.host.items if item.has_icons]

    def calculate_length(self):
        if not self.host.items:
            return 0

        return len(self.available_icons) * (self.icon_size + self.padding) + self.padding

    def _configure(self, qtile, bar):
        if self.configured:
            return

        self.host = host
        self.host.display_menu_callback = self.display_menu
        if has_xdg and self.icon_theme:
            self.host.icon_theme = self.icon_theme

        # This is called last as it starts timers including _config_async.
        base._Widget._configure(self, qtile, bar)

    async def _config_async(self):
        await self.host.start(self)

    def find_icon_at_pos(self, x, y):
        """returns StatusNotifierItem object for icon in given position"""
        xoffset = self.padding
        if x < xoffset:
            return None

        for icon in self.available_icons:
            xoffset += self.icon_size
            if x < xoffset:
                return icon
            xoffset += self.padding

        return None

    def button_press(self, x, y, button):
        icon = self.find_icon_at_pos(x, y)
        if not icon:
            return

        name = 'Button{0}'.format(button)
        if name in self.mouse_callbacks:
            self.mouse_callbacks[name](icon)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        if self.bar.horizontal:
            xoffset = self.padding
            yoffset = (self.height - self.icon_size) // 2

            for item in self.available_icons:
                icon = item.get_icon(self.icon_size)
                self.drawer.ctx.set_source_surface(icon, xoffset, yoffset)
                self.drawer.ctx.paint()

                xoffset += self.icon_size + self.padding

            self.drawer.draw(offsetx=self.offset, width=self.length)

        else:
            xoffset = (self.width - self.icon_size) // 2
            yoffset = self.padding

            for item in self.available_icons:
                icon = item.get_icon(self.icon_size)
                self.drawer.ctx.set_source_surface(icon, xoffset, yoffset)
                self.drawer.ctx.paint()

                yoffset += self.icon_size + self.padding

            self.drawer.draw(offsety=self.offset, height=self.length)

    def activate(self, item):
        """Primary action when clicking on an icon"""
        if item.is_context_menu:
            self.show_menu(item)
        else:
            item.activate()

    def show_menu(self, item):
        item.get_menu()

    def display_menu(self, menu_items):
        menu = PopupMenu.from_dbus_menu(self.qtile, menu_items, **self.menu_config)

        screen = self.bar.screen

        if screen.top == self.bar:
            x = min(self.offsetx, self.bar.width - menu.width)
            y = self.bar.height

        elif screen.bottom == self.bar:
            x = min(self.offsetx, self.bar.width - menu.width)
            y = screen.height - self.bar.height - menu.height

        elif screen.left == self.bar:
            x = self.bar.width
            y = min(self.offsety, screen.height - menu.height)

        else:
            x = screen.width - self.bar.width - menu.width
            y = min(self.offsety, screen.height - menu.height)

        menu.show(x, y)
