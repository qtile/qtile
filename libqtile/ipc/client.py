from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from libqtile.ipc.stream import IPCStreamIO
from libqtile.utils import create_task

if TYPE_CHECKING:
    pass


from libqtile.ipc import IPCError
from libqtile.ipc.messages import (
    IPCCommandMessage,
    IPCEventsSubscribeMessage,
    IPCEventsUnsubscribeMessage,
    IPCMessage,
    IPCReplRequestMessage,
    IPCReplStartMessage,
    IPCReplStopMessage,
    IPCReplyMessage,
    IPCStatus,
)


class ReconnectingClient:
    def __init__(self, socket_path: str) -> None:
        """Create a new IPC client

        Parameters
        ----------
        socket_path: str
            The file path to the file that is used to open the connection to
            the running IPC server.
        """
        self.socket_path = socket_path

    def call(self, data: tuple) -> IPCReplyMessage:
        return self.send(data)

    def send(self, msg: tuple) -> IPCReplyMessage:
        """Send the message and return the response from the server

        If any exception is raised by the server, that will propagate out of
        this call.
        """
        return asyncio.run(self.async_send(msg))

    async def async_send(self, msg: tuple) -> IPCReplyMessage:
        """Send the message to the server

        Connect to the server, then pack and send the message to the server,
        then wait for and return the response from the server.
        """
        async with AsyncClient(self.socket_path) as c:
            return await c.command(IPCCommandMessage(*msg))


Client = ReconnectingClient


class AsyncClient:
    def __init__(self, socket_path: str) -> None:
        """Create a new asynchronous IPC client

        Parameters
        ----------
        socket_path: str
            The file path to the file that is used to open the connection to
            the running IPC server.
        """
        self.socket_path = socket_path
        self.stream: IPCStreamIO | None = None
        self.listen_task: asyncio.Task | None = None
        self.listening = False

    async def connect(self):
        """Open the unix domain socket connection to the IPC server"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(path=self.socket_path), timeout=3
            )
            self.stream = IPCStreamIO(reader, writer)
        except (ConnectionRefusedError, FileNotFoundError):
            raise IPCError(f"Could not open {self.socket_path}")
        except TimeoutError:
            raise IPCError("Connection to server timed out")

    def is_connected(self) -> bool:
        return self.stream is not None

    async def send(self, message: IPCMessage) -> IPCReplyMessage:
        """Send the message to the server using the existing connection."""
        if self.stream is None:
            raise IPCError("AsyncClient is not connected, use 'async with' or call 'connect'")

        try:
            await self.stream.write_message(message)

            response = await self.stream.read_message(timeout=10.0)
            if not isinstance(response, IPCReplyMessage):
                raise IPCError("Expected a reply message from the server")

            return response
        except TimeoutError:
            raise IPCError("Server not responding")

    async def _listen_loop(self, callback: Callable[[IPCMessage], Any]):
        """Continuously listen for incoming messages pushed by the server (broadcasts/events)."""
        try:
            while self.listening and self.stream is not None:
                message = await self.stream.read_message()
                if message is None:
                    break

                result = callback(message)
                if asyncio.iscoroutine(result):
                    await result
        except asyncio.CancelledError:
            pass
        except Exception:
            if self.stream:
                await self.close()
        finally:
            self.listening = False

    async def command(self, command: IPCCommandMessage) -> IPCReplyMessage:
        return await self.send(command)

    async def repl_start(self) -> IPCReplyMessage:
        return await self.send(IPCReplStartMessage())

    async def repl_stop(self, session_id) -> IPCReplyMessage:
        return await self.send(IPCReplStopMessage(session_id))

    async def repl_request(self, session_id, data: dict[str, Any]) -> IPCReplyMessage:
        return await self.send(IPCReplRequestMessage(session_id, data))

    async def events_subscribe(
        self,
        events: list[str],
        callback: Callable[[IPCMessage], Any],
    ) -> IPCReplyMessage:
        msg = await self.send(IPCEventsSubscribeMessage(events))
        if msg.status == IPCStatus.SUCCESS:
            self.start_listening(callback)
        return msg

    def start_listening(self, callback: Callable[[IPCMessage], Any]) -> None:
        self.listening = True
        self.listen_task = create_task(self._listen_loop(callback))

    async def stop_listening(self):
        self.listening = False
        if self.listen_task is not None:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
            self.listen_task = None

    async def events_unsubscribe(self) -> IPCReplyMessage:
        return await self.send(IPCEventsUnsubscribeMessage())

    async def close(self):
        await self.stop_listening()

        if self.stream is not None:
            await self.stream.close()
            self.stream = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        await self.close()
