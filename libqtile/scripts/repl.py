from __future__ import annotations

import codeop
import re
import sys
from typing import TYPE_CHECKING

from libqtile.ipc import PersistentClient, find_sockfile

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.patch_stdout import patch_stdout

    HAS_PT = True
except (ImportError, ModuleNotFoundError):
    HAS_PT = False

if TYPE_CHECKING:
    pass


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


def start_repl(_args):
    if not HAS_PT:
        sys.exit("You need to install prompt_toolkit to use the REPL client.")

    with PersistentClient(find_sockfile()) as client:
        welcome_message = client.repl_start().data["output"]

        # Create the objects needed for the client
        class SocketCompleter(Completer):
            def __init__(self, client):
                self.client = client

            def get_completions(self, document, _complete_event):
                text_before_cursor = document.text_before_cursor

                # Extract the current word or attribute expression (e.g., qtile.cur)
                match = re.search(r"([\w\.]+)$", text_before_cursor)
                if not match:
                    return

                word = match.group(1)
                start_position = -len(word)

                # Send only the word to the REPL server
                matches = self.client.repl_request({"completion": word}).data["matches"]

                # Filter out empty strings
                options = list(filter(None, matches))

                # No suggestions so return early
                if not options:
                    return

                for opt in options:
                    # opt is the full completion (e.g. 'qtile.current_layout')
                    yield Completion(opt, start_position=start_position)

        kb = KeyBindings()
        completer = SocketCompleter(client)

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

                # Submit to server
                response = client.repl_request({"code": text}).data["output"]

                # Save our code to the history as `buffer.reset()`
                # would otherwise prevent that from happening
                session.history.append_string(text)

                # Clear buffer before reading response
                buffer.reset()

                # Echo input and response manually
                text = text.replace("\n", "\n... ")
                print(f">>> {text}")
                if response.strip():
                    print(response, end="\n", flush=True)
            else:
                buffer.insert_text("\n")  # Insert a newline instead

        with patch_stdout():
            # Read the welcome message from the server.
            print(welcome_message, end="", flush=True)

            while True:
                try:
                    session.prompt(">>> ")
                except KeyboardInterrupt:
                    print("\nExiting.")
                    break


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser("repl", parents=parents, help="Run a qtile REPL session.")
    parser.set_defaults(func=start_repl)
