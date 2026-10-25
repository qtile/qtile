from __future__ import annotations

import asyncio
import fcntl
import os.path
import socket
from collections.abc import Callable
from typing import TYPE_CHECKING, Self

from libqtile.ipc import IPCError
from libqtile.ipc.events import EventClient, EventServer
from libqtile.ipc.messages import (
    IPCCommandMessage,
    IPCEventsSubscribeMessage,
    IPCEventsUnsubscribeMessage,
    IPCReplRequestMessage,
    IPCReplStartMessage,
    IPCReplStopMessage,
    IPCReplyMessage,
)
from libqtile.ipc.repl import QtileREPL
from libqtile.ipc.stream import IPCStreamIO
from libqtile.log_utils import logger

if TYPE_CHECKING:
    pass


class Server:
    def __init__(
        self, socket_path: str, handler: Callable[[IPCCommandMessage], IPCReplyMessage], qtile
    ) -> None:
        self.socket_path = socket_path
        self.handler = handler
        # Needed to initiate a QtileREPL. This feels a bit dirty,
        # especially since we already pass an indirect reference to
        # the qtile instance in `handler`, because `IPCCommandServer`
        # holds a reference to `qtile` as well
        self.qtile = qtile
        self.server = None  # type: asyncio.AbstractServer | None
        self.repl = QtileREPL()
        self.events_server = EventServer()

        if os.path.exists(socket_path):
            os.unlink(socket_path)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        flags = fcntl.fcntl(self.sock.fileno(), fcntl.F_GETFD)
        fcntl.fcntl(self.sock.fileno(), fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        old_umask = os.umask(0o177)
        try:
            self.sock.bind(self.socket_path)
        finally:
            os.umask(old_umask)

    async def _server_callback(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Callback when a connection is made to the server

        Read the data sent from the client, execute the requested command, and
        send the reply back to the client.
        """
        stream = IPCStreamIO(reader, writer)
        event_client: EventClient | None = None
        logger.debug("Connection made to server")
        try:
            while True:
                # There is no timeout here to enable long lived connections
                # by clients, without having to implement a heartbeat protocol
                # which would impose a huge burden on the current implementation.
                # Clients are assumed to be trusted, although there is no actual
                # verification mechanism for this
                req = await stream.read_message()

                # EOF
                if req is None:
                    logger.debug("Client disconnected")
                    break

                else:
                    # Interactivity should be disable when the session is locked.
                    check_locked = False
                    match req:
                        case IPCCommandMessage():
                            # The handler shouldn't throw, but return an
                            # `IPCReplyMessage` with `IPCStatus.EXCEPTION`
                            # No need to check the locked status as the IPCCommandServer does that for us
                            rep = self.handler(req)

                        case IPCReplStartMessage():
                            check_locked = True
                            rep = IPCReplyMessage.success(self.repl.new_client(self.qtile))

                        case IPCReplStopMessage():
                            check_locked = True
                            disconnected = self.repl.remove_client(req.session_id)
                            if disconnected:
                                rep = IPCReplyMessage.success("Client disconnected.")
                            else:
                                rep = IPCReplyMessage.error(
                                    "Could not disconnect client: Invalid session_id."
                                )

                        # As mentioned in `MessageType`, it's possible to handle
                        # the repl being None by just creating one on demand,
                        # as the repl isn't really "running" at all, and getting
                        # rid of the `REPL_START` message type
                        case IPCReplRequestMessage():
                            check_locked = True
                            rep = IPCReplyMessage.success(
                                await self.repl.handle(req.session_id, req.data)
                            )

                        case IPCEventsSubscribeMessage():
                            if not self.events_server.clients:
                                self.events_server.start(self.qtile)
                            event_client = EventClient(stream, req.events)
                            self.events_server.clients.add(event_client)
                            rep = IPCReplyMessage.success("Subscribe successful.")

                        case IPCEventsUnsubscribeMessage():
                            if event_client is not None:
                                self.events_server.remove_client(event_client)
                                event_client = None
                                rep = IPCReplyMessage.success("Unsubscribe successful.")
                            else:
                                rep = IPCReplyMessage.error("No client subscribed.")

                        case _:
                            raise IPCError(f"Invalid request received: {req.message_type}")

                    if check_locked and self.qtile.locked:
                        rep = IPCReplyMessage.error(
                            "IPC interactivity is disabled when the session is locked."
                        )

                logger.debug("Sending result")

                await stream.write_message(rep)
        # Consider trying to send the client an
        # `IPCReplyMessage` with `IPCStatus.EXCEPTION`
        except IPCError as e:
            logger.warning("Invalid data received, closing connection")
            logger.debug(e)
        finally:
            logger.debug("Closing connection")
            await stream.close()

    async def __aenter__(self) -> Self:
        """Start and return the server"""
        await self.start()
        return self

    async def __aexit__(self, _exc_type, _exc_value, _tb) -> None:
        """Close and shutdown the server"""
        await self.close()

    async def start(self) -> None:
        """Start the server"""
        assert self.server is None

        logger.debug("Starting server")
        server_coroutine = asyncio.start_unix_server(self._server_callback, sock=self.sock)
        self.server = await server_coroutine

    async def close(self) -> None:
        """Close and shutdown the server"""
        assert self.server is not None

        logger.debug("Stopping server on close")
        self.server.close()
        await self.server.wait_closed()

        self.server = None
