# Copyright (c) 2010 dequis
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2013 Mickael FALCK
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2020 elParaguayo
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

from typing import Any

try:
    from dbus_next.aio import MessageBus
    from dbus_next.service import ServiceInterface
    from dbus_next.service import method, signal
    has_dbus = True
except ImportError:
    has_dbus = False

from libqtile.log_utils import logger

BUS_NAME = 'org.freedesktop.Notifications'
SERVICE_PATH = '/org/freedesktop/Notifications'

notifier: Any = None


class ClosedReason:
    expired = 1
    dismissed = 2
    method = 3  # CloseNotification method


if has_dbus:
    class NotificationService(ServiceInterface):
        def __init__(self, manager):
            super().__init__(BUS_NAME)
            self.manager = manager
            self._capabilities = {'body'}

        @method()
        def GetCapabilities(self) -> 'as':  # type:ignore  # noqa: N802, F722
            return list(self._capabilities)

        def register_capabilities(self, capabilities):
            if isinstance(capabilities, str):
                self._capabilities.add(capabilities)
            elif isinstance(capabilities, (tuple, list, set)):
                self._capabilities.update(set(capabilities))

        @method()
        def Notify(self,  # noqa: N802, F722
                   app_name: 's', replaces_id: 'u',  # type:ignore  # noqa: F821
                   app_icon: 's', summary: 's',  # type:ignore  # noqa: F821
                   body: 's', actions: 'as',  # type:ignore  # noqa: F821
                   hints: 'a{sv}', timeout: 'i') -> 'u':  # type:ignore  # noqa: F821
            notif = Notification(
                summary, body, timeout, hints, app_name, replaces_id, app_icon, actions
            )
            return self.manager.add(notif)

        @method()
        def CloseNotification(self, nid: 'u'):  # type:ignore  # noqa: N802, F821
            self.manager.close(nid)

        @signal()
        def NotificationClosed(self, nid: 'u', reason: 'u') -> 'uu':  # type:ignore  # noqa: N802, F821
            return [nid, reason]

        @signal()
        def ActionInvoked(self, nid: 'u', action_key: 's') -> 'us':  # type:ignore  # noqa: N802, F821
            return [nid, action_key]

        @method()
        def GetServerInformation(self) -> 'ssss':  # type:ignore  # noqa: N802, F821
            return ["qtile-notify-daemon", "qtile", "1.0", "1"]

    class Notification:
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
            self.notifications = []
            self.callbacks = []
            self.close_callbacks = []
            self._service = None

        async def service(self):
            if self._service is None:
                try:
                    bus = await MessageBus().connect()
                    self._service = NotificationService(self)
                    bus.export(SERVICE_PATH, self._service)
                    await bus.request_name(BUS_NAME)
                except Exception:
                    logger.exception('Dbus connection failed')
                    self._service = None
            return self._service

        async def register(self, callback, capabilities=None, on_close=None):
            service = await self.service()
            if not service:
                logger.warning(
                    'Registering %s without any dbus connection existing',
                    callback.__name__,
                )
            self.callbacks.append(callback)
            if capabilities:
                self._service.register_capabilities(capabilities)
            if on_close:
                self.close_callbacks.append(on_close)

        def add(self, notif):
            self.notifications.append(notif)
            notif.id = len(self.notifications)
            for callback in self.callbacks:
                try:
                    callback(notif)
                except Exception:
                    logger.exception("Exception in notifier callback")
            return len(self.notifications)

        def show(self, *args, **kwargs):
            notif = Notification(*args, **kwargs)
            return (notif, self.add(notif))

        def close(self, nid):
            notif = self.notifications[nid]

            for callback in self.close_callbacks:
                try:
                    callback(notif)
                except Exception:
                    logger.exception("Exception in notifier close callback")

    notifier = NotificationManager()

else:

    class FakeManager:
        def __init__(self):
            logger.warning(
                "dbus-next is not installed. "
                "Notification service and widget are unavailable."
            )

        async def register(self, *args, **kwargs):
            pass

    notifier = FakeManager()
