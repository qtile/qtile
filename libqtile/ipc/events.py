from __future__ import annotations

import asyncio
import contextlib
import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libqtile import hook
from libqtile.ipc import IPCError
from libqtile.ipc.messages import IPCEventsNotifyMessage
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

PROTOCOL_VERSION = 1

# Clients whose unsent backlog exceeds this are disconnected rather than
# allowed to grow qtile's memory use or stall the event loop.
MAX_WRITE_BUFFER = 256 * 1024

# Longest line we accept from a client.
MAX_LINE = 64 * 1024

WILDCARD = "*"

# Unpaired surrogates are not valid Unicode and so are not allowed in I-JSON strings.
SURROGATES = re.compile("[\ud800-\udfff]")

serializers: list[tuple[type, Callable[[Any], Any]]] | None = None


def load_serializers() -> list[tuple[type, Callable[[Any], Any]]]:
    """Defines a list of serialisers for qtile object types."""
    from libqtile.backend.base import Window
    from libqtile.config import Screen
    from libqtile.group import _Group
    from libqtile.layout.base import Layout

    def window(w: Window) -> dict[str, Any]:
        group = getattr(w, "group", None)
        return {
            "wid": w.wid,
            "name": w.name,
            "group": group.name if group is not None else None,
        }

    def group(g: _Group) -> dict[str, Any]:
        return {
            "name": g.name,
            "windows": [window(w) for w in g.windows],
            "screen": screen(g.screen) if g.screen else None,
        }

    def screen(s: Screen) -> dict[str, Any]:
        return {"index": s.index}

    def layout(layout_: Layout) -> dict[str, Any]:
        return {"name": layout_.name}

    return [
        (Window, window),
        (_Group, group),
        (Screen, screen),
        (Layout, layout),
    ]


@dataclass(eq=False)
class EventClient:
    stream: Any
    # None means "everything".
    events: list[str] | None = None

    def wants(self, event: str) -> bool:
        return not self.events or event in self.events


class EventServer:
    """
    Publish qtile hook events to subscribed clients.

    Clients connect to a Unix socket (default is current qtile socket plus ".events").
    Every message, in both directions, is a single JSON object terminated by a newline.
    Every message has a ``type`` member. Receivers ignore unknown types and unknown members.

    Client -> server:

        {"type": "subscribe", "events": ["client_new", "setgroup"]}   replace the event filter
        {"type": "subscribe", "events": null}                         receive everything (default)
        {"type": "subscribe", "events": ["*"]}                        receive everything

    Server -> client:

        {"type": "hello", "version": 1}
        {"type": "event", "event": "<hook name>", "args": [<jsonable>, ...]}

    ``args`` mirror what the hook was fired with, converted to serialisable data with
    `to_jsonable`. A ``kwargs`` object is added only if the hook was fired with keyword arguments.
    """

    def __init__(self) -> None:
        self.clients: set[EventClient] = set()
        hook.add_observer(self.publish)
        self.serializers: list[tuple[type, Callable[[Any], Any]]] = []
        self.loop: asyncio.AbstractEventLoop | None = None

    def start(self, qtile) -> None:
        self.serializers = load_serializers()
        self.loop = qtile._eventloop

    def stop(self) -> None:
        hook.remove_observer(self.publish)
        for client in list(self.clients):
            self.remove_client(client)

    def to_jsonable(self, obj: Any, _depth: int = 0) -> Any:
        """
        Convert a hook argument into something ``json.dumps`` accepts.

        Known qtile objects become small dicts of stable fields. Unknown objects
        fall back to ``repr`` so that a new hook argument type can never break the
        feed. The result is valid JSON (and I-JSON): non-finite floats become
        ``None`` and unpaired surrogates in strings are replaced.
        """
        global serializers

        if obj is None or isinstance(obj, (bool, int)):
            return obj
        if isinstance(obj, float):
            return obj if math.isfinite(obj) else None
        if isinstance(obj, str):
            return SURROGATES.sub("\ufffd", obj)
        if _depth > 4:
            return repr(obj)
        if isinstance(obj, (list, tuple, set)):
            return [self.to_jsonable(o, _depth + 1) for o in obj]
        if isinstance(obj, dict):
            return {
                SURROGATES.sub("\ufffd", str(k)): self.to_jsonable(v, _depth + 1)
                for k, v in obj.items()
            }

        for cls, fn in self.serializers:
            if isinstance(obj, cls):
                try:
                    return fn(obj)
                except Exception:
                    logger.exception("Failed to serialize %r", obj)
                    return repr(obj)
        return repr(obj)

    def publish(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Publish an event to subscribed clients.

        Must be called on the event loop's thread, like ``hook.fire``.
        """
        # This is really more for mypy and should not really be possible...
        if self.loop is None:
            raise IPCError("Events server publishing messages before setting event loop.")

        targets = [c for c in self.clients if c.wants(event)]
        if not targets:
            return

        message = IPCEventsNotifyMessage(
            event,
            [self.to_jsonable(a) for a in args],
            {k: self.to_jsonable(v) for k, v in kwargs.items()},
        )
        for client in targets:
            asyncio.run_coroutine_threadsafe(self._safe_write(client, message), self.loop)

    async def _safe_write(self, client: EventClient, message: IPCEventsNotifyMessage) -> None:
        """Safely write to client and handle any dropouts without unhandled exceptions."""
        try:
            transport = client.stream.writer.transport
            if transport.is_closing():
                self.remove_client(client)
            elif transport.get_write_buffer_size() > MAX_WRITE_BUFFER:
                logger.warning("Disconnecting slow event-feed client")
                self.remove_client(client)
            else:
                await client.stream.write_message(message)
        except Exception:
            # If writing fails, cleanly remove the client
            self.remove_client(client)

    def remove_client(self, client: EventClient) -> None:
        self.clients.discard(client)
        # abort(), not close(): close() flushes the write buffer first, which never
        # finishes for a stuck client, leaving the socket open and blocking stop().
        with contextlib.suppress(Exception):
            client.stream.writer.transport.abort()
