# Copyright (c) 2010 dequis
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2013 Mickael FALCK
# Copyright (c) 2013 Tao Sauvage
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

"""
    If dbus is available, this module implements a
    org.freedesktop.Notifications service.
"""
from collections import OrderedDict
from enum import Enum
from threading import RLock, Thread, current_thread, main_thread

from libqtile.log_utils import logger

try:
    import dbus
    from dbus import service
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)
    has_dbus = True
except ImportError:
    has_dbus = False


BUS_NAME = 'org.freedesktop.Notifications'
SERVICE_PATH = '/org/freedesktop/Notifications'

if has_dbus:
    class NotificationService(service.Object):
        def __init__(self, manager):
            bus = dbus.SessionBus()
            bus.request_name(BUS_NAME)
            bus_name = service.BusName(BUS_NAME, bus=bus)
            service.Object.__init__(self, bus_name, SERVICE_PATH)
            self.manager = manager
            self._capabilities = {'body'}

        @service.method(BUS_NAME, in_signature='', out_signature='as')
        def GetCapabilities(self):  # noqa: N802
            return list(self._capabilities)

        def register_capabilities(self, capabilities):
            if isinstance(capabilities, str):
                self._capabilities.add(capabilities)
            elif isinstance(capabilities, (tuple, list, set)):
                self._capabilities.update(set(capabilities))

        @service.method(BUS_NAME, in_signature='susssasa{sv}i', out_signature='u')
        def Notify(self, app_name, replaces_id, app_icon, summary,  # noqa: N802
                   body, actions, hints, timeout):
            notif = Notification(
                summary, body, timeout, hints, app_name, replaces_id, app_icon, actions
            )
            return self.manager.add(notif)

        @service.method(BUS_NAME, in_signature='u', out_signature='')
        def CloseNotification(self, id):  # noqa: N802
            pass

        @service.signal(BUS_NAME, signature='uu')
        def NotificationClosed(self, id_in, reason_in):  # noqa: N802
            pass

        @service.method(BUS_NAME, in_signature='', out_signature='ssss')
        def GetServerInformation(self):  # noqa: N802
            return ("qtile-notify-daemon", "qtile", "1.0", "1")


class Notification:

    class Urgency(Enum):
        LOW = 0
        NORMAL = 1
        CRITICAL = 2

        def _missing_(self):
            try:
                # Default priority is NORMAL
                priority = self.hints.get('urgency', 1)
                return Notification.Urgency(int(priority))
            except (AttributeError, ValueError):
                return Notification.Urgency.NORMAL

    def __init__(self, summary, body='', timeout=-1, hints=None, app_name='',
                 replaces_id=None, app_icon=None, actions=None):
        self.summary = summary
        self.body = body
        self.timeout = timeout
        self.hints = hints or {}
        self.app_name = app_name
        self.replaces_id = replaces_id
        self.app_icon = app_icon
        self.actions = actions


class NotificationManager:
    def __init__(self):
        # Use OrderedDict to maintain order
        self._notifications = OrderedDict()
        # Use a dict for indexing for quick finding prev/next notification
        self._notifications_idx = dict()
        self._current_id = 0
        self.callbacks_add = []
        self.callbacks_delete = []
        self._service = None
        # Use a lock to protect notification concurrency.
        self._lock = RLock()

    @property
    def service(self):
        if has_dbus and self._service is None:
            try:
                self._service = NotificationService(self)
            except Exception:
                logger.exception('Dbus connection failed')
                self._service = None
        return self._service

    @property
    def notifications(self):
        with self._lock:
            return list(self._notifications.values())

    def prev(self, notification):
        # Can pass either notification id or the notification itself
        if isinstance(notification, int):
            notif_id = notification
        elif isinstance(notification, Notification):
            notif_id = notification.id
        else:
            return None

        with self._lock:
            notif_idx = self._notifications_idx.get(notif_id, None)
            if notif_idx is not None:
                prev_id = notif_idx['prev_id']
                prev_notif = self._notifications.get(prev_id, None)
                return prev_notif

            # There is a chance that the notification requested might be deleted.
            # In that case we need to loop the notifications to find the previous.
            prev_notif = None
            for notif in self._notifications.values():
                if notif.id >= notif_id:
                    break
                prev_notif = notif
            return prev_notif

    def next(self, notif):
        # Can pass either notification id or the notification itself
        if isinstance(notif, int):
            notif_id = notif
        elif isinstance(notif, Notification):
            notif_id = notif.id
        else:
            return None

        with self._lock:
            notif_idx = self._notifications_idx.get(notif_id, None)
            if notif_idx is not None:
                next_id = notif_idx['next_id']
                next_notif = self._notifications.get(next_id, None)
                return next_notif

            # There is a chance that the notification requested might be deleted.
            # In that case we need to loop the notifications to find the next.
            next_notif = None
            for notif in self._notifications.values():
                if notif.id > notif_id:
                    next_notif = notif
                    break
            return next_notif

    def register(self, callback, capabilities=None):
        if not self.service:
            logger.warning(
                'Registering %s without any dbus connection existing',
                callback.__name__,
            )
        self.callbacks_add.append(callback)
        if capabilities:
            self._service.register_capabilities(capabilities)

    def register_delete(self, callback):
        if not self.service:
            logger.warning(
                'Registering %s without any dbus connection existing',
                callback.__name__,
            )
        self.callbacks_delete.append(callback)

    def add(self, notif):
        with self._lock:
            # Find the id of the previous notification
            if self._notifications:
                prev_id = next(reversed(self._notifications))
                prev_id = self._notifications[prev_id].id
            else:
                prev_id = None

            self._current_id += 1
            notif.id = self._current_id
            self._notifications[notif.id] = notif
            # Assign prev_id to notifications indexing dict
            self._notifications_idx[notif.id] = dict(
                prev_id=prev_id,
                next_id=None
            )

            # Set next_id of previous notification to this notification's id.
            if prev_id is not None:
                self._notifications_idx[prev_id]['next_id'] = notif.id

            notifs_len = len(self._notifications)

        for callback in self.callbacks_add:
            # Don't let the subscriber crash us
            try:
                callback(notif)
            except Exception as e:
                logger.error(e)

        return notifs_len

    def delete(self, *notifs):
        """Delete one or more notifications given the notifications or their
        ids.
        """
        # Should not block the main thread
        if main_thread() == current_thread():
            Thread(target=self.delete, args=notifs).start()
            return
        notifs_deleted = []
        with self._lock:
            for notif in notifs:
                if isinstance(notif, int):
                    notif_id = notif
                elif isinstance(notif, Notification):
                    notif_id = notif.id
                else:
                    continue

                notif = self._notifications.get(notif_id, None)
                if notif is None:
                    continue
                notifs_deleted.append(notif)

                # Get previous and next ids for re-indexing
                notif_idx = self._notifications_idx[notif_id]
                prev_id = notif_idx['prev_id']
                next_id = notif_idx['next_id']

                # Next notification should point to previous of deleted
                if next_id is not None:
                    self._notifications_idx[next_id]['prev_id'] = prev_id

                # Previous notification should point to next of deleted
                if prev_id is not None:
                    self._notifications_idx[prev_id]['next_id'] = next_id

                del self._notifications_idx[notif_id]
                del self._notifications[notif_id]

        # Do nothing if nothing was deleted
        if len(notifs_deleted) == 0:
            return

        for callback in self.callbacks_delete:
            # Don't let the subscriber crash us
            try:
                callback(*notifs_deleted)
            except Exception as e:
                logger.error(e)

    def delete_all(self):
        with self._lock:
            notifs_deleted = self._notifications.values()
            self._notifications = OrderedDict()
            self._notifications_idx = {}

        for callback in self.callbacks_delete:
            # Don't let the subscriber crash us
            try:
                callback(*notifs_deleted)
            except Exception as e:
                logger.error(e)

    def show(self, *args, **kwargs):
        notif = Notification(*args, **kwargs)
        return (notif, self.add(notif))


notifier = NotificationManager()
