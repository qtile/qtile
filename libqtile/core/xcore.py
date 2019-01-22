import asyncio
import typing

from . import base
from . import xcbq

from xcffib.xproto import WindowError, AccessError, DrawableError
import xcffib.xproto

_IgnoredEvents = set([
    xcffib.xproto.KeyReleaseEvent,
    xcffib.xproto.ReparentNotifyEvent,
    xcffib.xproto.CreateNotifyEvent,
    # DWM handles this to help "broken focusing windows".
    xcffib.xproto.MapNotifyEvent,
    xcffib.xproto.LeaveNotifyEvent,
    xcffib.xproto.FocusOutEvent,
    xcffib.xproto.FocusInEvent,
    xcffib.xproto.NoExposureEvent
])


class XCore(base.Core):
    conn: xcbq.Connection

    def start(self, display: str, loop: asyncio.AbstractEventLoop, q: asyncio.queues.Queue) -> None:
        self._loop = loop
        self.q = q
        self.conn = xcbq.Connection(display)
        self.conn.xsync()
        self._loop.add_reader(
            self.conn.conn.get_file_descriptor(),
            self._xpoll
        )

    def _xpoll(self):
        while True:
            try:
                e = self.conn.conn.poll_for_event()
            except xcffib.ConnectionException:
                return
            except (WindowError, AccessError, DrawableError):
                # Since X is event based, race conditions can occur almost
                # anywhere in the code. For example, if a window is created and
                # then immediately destroyed (before the event handler is
                # evoked), when the event handler tries to examine the window
                # properties, it will throw a WindowError exception. We can
                # essentially ignore it, since the window is already dead and
                # we've got another event in the queue notifying us to clean it
                # up.
                continue
            except Exception as e:
                message = "Exception in core loop: %s" % str(e)
                error_code = self.conn.conn.has_error()
                if error_code:
                    error_string = xcbq.XCB_CONN_ERRORS[error_code]
                    message = "X connection error: %s (%s)" % (error_string, error_code)
                self.q.put_nowait(base.ShutdownEvent(message))
                return

            if not e:
                break

            if e.__class__ not in _IgnoredEvents:
                self.q.put_nowait(e)

        self.conn.flush()

    def get_keys(self) -> typing.List[str]:
        return list(xcbq.keysyms.keys())

    def get_modifiers(self) -> typing.List[str]:
        return list(xcbq.ModMasks.keys())
