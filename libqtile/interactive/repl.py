# Copyright (c) 2025, elParaguayo. All rights reserved.
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
import builtins
import codeop
import contextlib
import io
import re
import traceback

from libqtile.log_utils import logger
from libqtile.utils import create_task

ATTR_MATCH = re.compile(r"([\w\.]+?)(?:\.([\w]*))?$")
TERMINATOR = "___END___"
COMPLETION_REQUEST = "___COMPLETE___::"
REPL_PORT = 41414


def mark_unavailable(func):
    def _wrapper(*args, **kwargs):
        print(f"'{func.__name__}' is disabled in this REPL.")

    return _wrapper


def make_safer_env():
    """
    Returns a dict to be passed to the REPL's global environment.

    Can be used to block harmful commands.
    """

    # Interactive help blocks REPL and will cause qtile to hand
    original_help = builtins.help

    def safe_help(*args):
        """Print help on a specified object."""
        if not args:
            print("Interactive help() is disabled in this REPL.")
        else:
            return original_help(*args)

    # Store original help so we can still call it safely
    builtins.help = safe_help

    # Mask other builtins
    builtins.input = mark_unavailable(builtins.input)

    return {"__builtins__": builtins}


def parse_completion_expr(text):
    """
    Parses an input like 'qtile.win' or 'qtil' and splits it into:
    - object_expr: what to evaluate or look up ('qtile', 'qtil')
    - attr_prefix: what to complete ('', 'win', etc.)
    """
    match = ATTR_MATCH.search(text)
    if not match:
        return None, None
    obj_expr, attr_prefix = match.groups()
    return obj_expr, attr_prefix or ""


def get_completions(text, local_vars):
    expr, attr_prefix = parse_completion_expr(text)

    # Case 1: Completing a top-level variable name
    if "." not in text:
        return [name for name in local_vars if name.startswith(expr)]

    # Case 2: Completing an attribute
    try:
        base = eval(expr, {}, local_vars)
        options = [attr for attr in dir(base) if attr.startswith(attr_prefix)]
        options = [
            f"{expr}.{attr}" + ("(" if callable(getattr(base, attr)) else "") for attr in options
        ]
        options = list(filter(None, options))
        return options
    except Exception:
        return []


class QtileREPLServer:
    """
    Provides a REPL interface to allow users to inspect qtile's internals via
    a more intuitive/familiar interface compared to `qtile shell`.
    """

    def __init__(self):
        self.buffer = ""
        self.compiler = codeop.Compile()
        self.started = False
        self.connections = set()

    def evaluate_code(self, code):
        with io.StringIO() as stdout:
            # Capture any stdout and direct to a buffer
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stdout):
                try:
                    try:
                        # Try eval (for expressions)
                        expr_code = compile(code, "<stdin>", "eval")
                        result = eval(expr_code, self.locals)
                        if result is not None:
                            # We can use print here as we've redirected stdout
                            print(repr(result))
                    except SyntaxError:
                        # Fallback to exec (for statements)
                        exec(self.compiler(code), self.locals)
                except Exception:
                    traceback.print_exc()

            return stdout.getvalue()

    async def handle_client(self, reader, writer):
        """Method for sending data to REPL client."""

        async def send(message, end=True):
            """Wrapper to send data to client."""
            suffix = TERMINATOR if end else ""
            writer.write(f"{message}{suffix}\n".encode())
            await writer.drain()

        await send("Connected to Qtile REPL\nPress Ctrl+C to exit.\n")

        # Keep track of the number of connected clients so server is not
        # stopped while there is still a client connected.
        task = asyncio.current_task()
        self.connections.add(task)

        self.compiler = codeop.CommandCompiler()

        while not reader.at_eof():
            buffer = ""
            # The client handles checking when a code block is complete and
            # terminates the code with a marker. Server therefore just reads
            # until it finds that marker.
            while True:
                line = await reader.readline()
                if not line:
                    break
                line = line.decode()

                if line.strip() == TERMINATOR:
                    break

                buffer += line

            # Handle completion requests
            if buffer.startswith(COMPLETION_REQUEST):
                prefix = buffer.split("::", 1)[1]
                matches = get_completions(prefix, self.locals)
                output = ",".join(matches) + "\n"
                await send(output)
                continue

            if not buffer.strip():
                buffer = ""
                await send("", end=False)
                continue

            # Ready to execute
            output = ""

            # Evaluate code in a thread so blocking calls don't block the eventloop
            loop = asyncio.get_running_loop()
            output = await loop.run_in_executor(None, self.evaluate_code, buffer)

            # Send output to client
            await send(output.strip())

        # Client has disconnected. Tidy up.
        writer.close()
        self.connections.remove(task)

    async def start(self, locals_dict=dict()):
        if self.started:
            return

        self.locals = {**make_safer_env(), **locals_dict}
        self.server = await asyncio.start_server(self.handle_client, "localhost", REPL_PORT)
        logger.info("Qtile REPL server running on localhost:%d", REPL_PORT)
        self.started = True

        # serve_forever() cannot be stopped except by putting it in a task and
        # cancelling that task.
        self.repl_task = create_task(self.server.serve_forever())

        try:
            await self.repl_task
        except asyncio.CancelledError:
            logger.info("Qtile REPL server has been stopped.")

    async def stop(self):
        if not self.started:
            return

        if self.connections:
            logger.debug("Can't close with active connections")
            return

        self.server.close()
        await self.server.wait_closed()
        self.repl_task.cancel()
        self.started = False


repl_server = QtileREPLServer()
