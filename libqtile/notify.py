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

        @service.method(BUS_NAME, in_signature='', out_signature='as')
        def GetCapabilities(self):  # noqa: N802
            return ('body')

        @service.method(BUS_NAME, in_signature='susssasa{sv}i', out_signature='u')
        def Notify(self, app_name, replaces_id, app_icon, summary,  # noqa: N802
                   body, actions, hints, timeout):
            notif = Notification(summary, body, timeout, hints)
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
    def __init__(self, summary, body='', timeout=-1, hints=None):
        self.summary = summary
        self.hints = hints or {}
        self.body = body
        self.timeout = timeout


class NotificationManager:
    def __init__(self):
        self.notifications = []
        self.callbacks = []
        self._service = None

    @property
    def service(self):
        if has_dbus and self._service is None:
            try:
                self._service = NotificationService(self)
            except Exception:
                logger.exception('Dbus connection failed')
                self._service = None
        return self._service

    def register(self, callback):
        if not self.service:
            logger.warning(
                'Registering %s without any dbus connection existing',
                callback.__name__,
            )
        self.callbacks.append(callback)

    def add(self, notif):
        self.notifications.append(notif)
        notif.id = len(self.notifications)
        for callback in self.callbacks:
            callback(notif)
        return len(self.notifications)

    def show(self, *args, **kwargs):
        notif = Notification(*args, **kwargs)
        return (notif, self.add(notif))


notifier = NotificationManager()
