from __future__ import annotations

import asyncio
import struct
from typing import TYPE_CHECKING

from libqtile.ipc import IPCError
from libqtile.ipc.messages import _IPC, IPCMessage
from libqtile.log_utils import logger

if TYPE_CHECKING:
    pass


class IPCStreamIO:
    """Wraps an asyncio `StreamReader` and `StreamWriter` and implements
    a simple framing protocol to handle sending and receiving IPCMessages
    """

    FRAME_HEADER_FORMAT = "!L"
    FRAME_HEADER_LENGTH = struct.calcsize(FRAME_HEADER_FORMAT)

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def write_frame(self, data: bytes):
        """Prepends the data with the frame header (length) and writes it to the writer"""
        frame_header = struct.pack(self.FRAME_HEADER_FORMAT, len(data))
        self.writer.write(frame_header)
        self.writer.write(data)
        await self.writer.drain()

    async def read_frame(self) -> bytes | None:
        """Reads the the frame header (length) and then reads and returns the expected
        number of bytes. Returns None if underlying stream has closed"""
        try:
            frame_header = await self.reader.readexactly(self.FRAME_HEADER_LENGTH)
            frame_length = struct.unpack(self.FRAME_HEADER_FORMAT, frame_header)[0]
            data = await self.reader.readexactly(frame_length)
            return data
        except asyncio.IncompleteReadError as e:
            if self.reader.at_eof():
                return None
            else:
                logger.debug(f"Received partial bytes: {e.partial!r}")
                raise IPCError("Invalid message framing, couldn't read the data")

    async def write_message(self, message: IPCMessage):
        await self.write_frame(_IPC.pack(message))

    async def read_message(self, *, timeout: float | None = None) -> IPCMessage | None:
        message_bytes = await asyncio.wait_for(self.read_frame(), timeout=timeout)
        if message_bytes is None:
            return None
        return _IPC.unpack(message_bytes)

    async def close(self):
        """Closes the connection"""
        self.writer.close()
        await self.writer.wait_closed()
