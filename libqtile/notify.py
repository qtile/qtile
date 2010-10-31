"""
    If dbus is available, importing this module enables the
    org.freedesktop.Notifications service. This will probably change.
"""

import hook

try:
    import dbus
except ImportError:
    dbus = None

if dbus:
    import gobject
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop

    BUS_NAME = 'org.freedesktop.Notifications'
    SERVICE_PATH = '/org/freedesktop/Notifications'

    class NotificationService(dbus.service.Object):
        def __init__(self, manager):
            bus_name = dbus.service.BusName(BUS_NAME, bus=dbus.SessionBus())
            dbus.service.Object.__init__(self, bus_name, SERVICE_PATH)
            self.manager = manager

        @dbus.service.method(BUS_NAME, in_signature='', out_signature='as')
        def GetCapabilities(self):
            # TODO: body, body-markup, icon-static
            return ()

        @dbus.service.method(BUS_NAME, in_signature='susssasa{sv}i',
                             out_signature='u')
        def Notify(self, app_name, replaces_id, app_icon, summary,
                   body, actions, hints, timeout):

            notif = Notification(summary, body, timeout=timeout)

            # useful hints:
            # urgency. how about making the notification red when it's urgent?
            # category. ignore?
            # image_data/icon_data 
            # x, y: where to point the notification
            print "Notification hints:"
            print dict([(str(x), y) for (x, y) in hints.iteritems()]).keys()

            return self.manager.add(notif)

        @dbus.service.method(BUS_NAME, in_signature='u', out_signature='')
        def CloseNotification(self, id):
            pass

        @dbus.service.signal(BUS_NAME, signature='uu')
        def NotificationClosed(self, id_in, reason_in):
            pass


    def init_main_loop():
        DBusGMainLoop(set_as_default=True)
        mainloop = gobject.MainLoop()

        def poll():
            mainloop.get_context().iteration(False)

        hook.subscribe.tick(poll)


class Notification(object):
    def __init__(self, summary, body='', timeout=-1):
        self.summary = summary
        self.body = body
        self.timeout = timeout
        print "Creating notification:", summary, body


class NotificationManager(object):
    def __init__(self):
        self.notifications = {}  # id : notification
        self.last_id = 0

        if dbus:
            init_main_loop()
            self.service = NotificationService(self)
        else:
            self.service = None

    def add(self, notif):
        self.last_id += 1
        self.notifications[self.last_id] = notif
        return self.last_id

    def show(self, *args, **kwargs):
        notif = Notification(*args, **kwargs)
        return notif, self.add(notif)


manager = NotificationManager()
