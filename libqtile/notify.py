"""
    If dbus is available, this module implements a
    org.freedesktop.Notifications service.
"""
import logging

try:
    import dbus
    from dbus import service
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    dbus = None

BUS_NAME = 'org.freedesktop.Notifications'
SERVICE_PATH = '/org/freedesktop/Notifications'

if dbus:
    class NotificationService(service.Object):
        def __init__(self, manager):
            bus_name = service.BusName(BUS_NAME, bus=dbus.SessionBus())
            super(NotificationServer, self).__init__(
                    bus_name,
                    SERVICE_PATH
            )
            self.manager = manager

        @service.method(BUS_NAME, in_signature='', out_signature='as')
        def GetCapabilities(self):
            return ('body')

        @service.method(BUS_NAME, in_signature='susssasa{sv}i',
                             out_signature='u')
        def Notify(self, app_name, replaces_id, app_icon, summary,
                   body, actions, hints, timeout):
            notif = Notification(summary, body, timeout, hints)
            return self.manager.add(notif)

        @service.method(BUS_NAME, in_signature='u', out_signature='')
        def CloseNotification(self, id):
            pass

        @service.signal(BUS_NAME, signature='uu')
        def NotificationClosed(self, id_in, reason_in):
            pass

        @service.method(BUS_NAME, in_signature='', out_signature='ssss')
        def GetServerInformation(self):
            return ("qtile-notify-daemon", "qtile", "1.0", "1")


class Notification(object):
    def __init__(self, summary, body='', timeout=-1, hints={}):
        self.summary = summary
        self.hints = hints
        self.body = body
        self.timeout = timeout


class NotificationManager(object):
    def __init__(self):
        self.notifications = []
        self.callbacks = []

        if dbus:
            try:
                DBusGMainLoop(set_as_default=True)
                self.service = NotificationService(self)
            except Exception:
                logging.getLogger('qtile').exception('Dbus init failed')
                self.service = None
        else:
            self.service = None

    def register(self, callback):
        self.callbacks.append(callback)

    def add(self, notif):
        self.notifications.append(notif)
        notif.id = len(self.notifications)
        for callback in self.callbacks:
            callback(notif)
        return len(self.notifications)

    def show(self, *args, **kwargs):
        notif = Notification(*args, **kwargs)
        return notif, self.add(notif)


notifier = NotificationManager()
