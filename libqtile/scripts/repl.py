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
from __future__ import annotations

import codeop
import re
import socket
import sys
from time import sleep
from typing import TYPE_CHECKING

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.patch_stdout import patch_stdout

    HAS_PT = True
except (ImportError, ModuleNotFoundError):
    HAS_PT = False

from libqtile.interactive.repl import COMPLETION_REQUEST, REPL_PORT, TERMINATOR
from libqtile.scripts.cmd_obj import cmd_obj

if TYPE_CHECKING:
    pass

HOST = "localhost"


class Command:
    """Wrapper to call commands via command interface."""

    def __init__(self, command, obj_spec=["root"], *args, **kwargs):
        self.function = command
        self.socket = None
        self.args = args
        self.kwargs = kwargs
        self.obj_spec = obj_spec
        self.info = False

    def __call__(self):
        return cmd_obj(self)


# Calls to start and stop the qtile REPL server
# Sends commands via qtile cmd-obj
start_server = Command("start_repl_server")
stop_server = Command("stop_repl_server")


def is_code_complete(text: str) -> bool:
    """Method to verify that we have a valid code block."""
    try:
        code_obj = codeop.compile_command(text, symbol="exec")

        # Incomplete (e.g. after 'def foo():')
        if code_obj is None:
            return False

        # Only treat as complete if there's a double blank line at the end for compound blocks
        lines = text.rstrip("\n").splitlines()
        return len(lines) <= 1 or text.endswith("\n\n")
    except (SyntaxError, OverflowError, ValueError, TypeError):
        return True


def read_full_response(sock, end_marker=f"{TERMINATOR}\n"):
    """Function to read data from socket until termination marker."""
    buffer = ""
    while True:
        data = sock.recv(4096).decode()

        if not data:
            # connection closed without end marker
            break

        buffer += data
        if end_marker in buffer:
            # Split off the marker and return only the response text
            response, _, _ = buffer.partition(end_marker)
            return response

    # connection closed without end marker
    return buffer


def start_repl(_args):
    if not HAS_PT:
        sys.exit("You need to install prompt_toolkit to use the REPL client.")

    # Start the repl server in qtile and find port number
    start_server()

    # We need to wait until server is up an running before continuing
    retry_count = 0
    while retry_count < 5:
        try:
            sock = socket.create_connection((HOST, REPL_PORT))
            break
        except ConnectionRefusedError:
            retry_count += 1
            sleep(0.5)

    if retry_count == 5:
        print("Unable to connect to REPL server. Exiting...")
        stop_server()
        return

    try:
        # Create the objects needed for the client
        class SocketCompleter(Completer):
            def __init__(self, sock):
                self.sock = sock

            def get_completions(self, document, _complete_event):
                text_before_cursor = document.text_before_cursor

                # Extract the current word or attribute expression (e.g., qtile.cur)
                match = re.search(r"([\w\.]+)$", text_before_cursor)
                if not match:
                    return

                word = match.group(1)
                start_position = -len(word)

                # Send only the word to the REPL server
                self.sock.sendall(f"{COMPLETION_REQUEST}{word}\n{TERMINATOR}\n".encode())

                # Read completions from server and filter out empty strings
                data = read_full_response(self.sock)
                options = list(filter(None, data.strip().split(",")))

                # No suggestions so return early
                if not options:
                    return

                for opt in options:
                    # opt is the full completion (e.g. 'qtile.current_layout')
                    yield Completion(opt, start_position=start_position)

        kb = KeyBindings()
        completer = SocketCompleter(sock)

        # Create a session instance
        session = PromptSession(
            completer=completer,
            key_bindings=kb,
            complete_while_typing=False,
            multiline=True,
            prompt_continuation=lambda *args, **kwargs: "... ",
            history=InMemoryHistory(),
        )

        # Create a handler for the Enter key so we can deal with multiline input
        @kb.add("enter")
        def _(event):
            buffer = event.app.current_buffer
            text = buffer.document.text

            if is_code_complete(text):
                # Save input line to print after
                full_block = f"{text}\n{TERMINATOR}\n"

                # Submit to server
                sock.sendall(full_block.encode())

                # Save our code to the history as `buffer.reset()`
                # would otherwise prevent that from happening
                session.history.append_string(text)

                # Clear buffer before reading response
                buffer.reset()

                # Read and print server response
                response = read_full_response(sock)

                # Echo input and response manually
                text = text.replace("\n", "\n... ")
                print(f">>> {text}")
                if response.strip():
                    print(response, end="\n", flush=True)
            else:
                buffer.insert_text("\n")  # Insert a newline instead

        with patch_stdout():
            # Read the welcome message from the server.
            print(read_full_response(sock), end="", flush=True)

            while True:
                try:
                    session.prompt(">>> ")
                except KeyboardInterrupt:
                    print("\nExiting.")
                    break

    finally:
        sock.close()
        stop_server()


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser("repl", parents=parents, help="Run a qtile REPL session.")
    parser.set_defaults(func=start_repl)
