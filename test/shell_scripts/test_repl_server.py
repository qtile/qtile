# Copyright (c) 2025 elParaguayo
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
import asyncio
import contextlib

import pytest

from libqtile.interactive.repl import (
    REPL_PORT,
    TERMINATOR,
    QtileREPLServer,
    get_completions,
)


def test_get_completions_top_level():
    local_vars = {"qtile": "dummy", "qtiles": 123}
    result = get_completions("qti", local_vars)
    assert "qtile" in result
    assert "qtiles" in result


def test_get_completions_attribute():
    class Dummy:
        def method(self):
            pass

        val = 42

    local_vars = {"dummy": Dummy()}
    result = get_completions("dummy.me", local_vars)
    assert "dummy.method(" in result

    result = get_completions("dummy.va", local_vars)
    assert "dummy.val" in result


def test_get_completions_invalid_expr():
    result = get_completions("invalid..expr", {})
    assert result == []


@pytest.mark.anyio
async def test_repl_server_executes_code():
    repl = QtileREPLServer()
    locals_dict = {"x": 123}

    # Start the REPL server in a background task
    start_task = asyncio.create_task(repl.start(locals_dict=locals_dict))

    # Wait for the server to bind the port
    await asyncio.sleep(0.1)

    reader, writer = await asyncio.open_connection("localhost", REPL_PORT)

    try:
        # Read welcome message
        welcome = await reader.read(4096)
        assert b"Connected to Qtile REPL" in welcome

        # Send a simple expression to evaluate
        writer.write(b"x\n" + f"{TERMINATOR}\n".encode())
        await writer.drain()

        # Read REPL result
        result = await reader.readuntil(f"{TERMINATOR}\n".encode())
        assert "123" in result.decode()

    finally:
        writer.close()
        await writer.wait_closed()

        # Stop the REPL server
        await repl.stop()

        # Cancel the server task
        start_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await start_task
