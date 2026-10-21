import asyncio
import codeop
import re
import sys
from typing import TYPE_CHECKING

from libqtile.ipc import AsyncClient, IPCStatus, find_sockfile

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
        if code_obj is None:
            return False
        lines = text.rstrip("\n").splitlines()
        return len(lines) <= 1 or text.endswith("\n\n")
    except (SyntaxError, OverflowError, ValueError, TypeError):
        return True


async def start_repl_async(_args):
    if not HAS_PT:
        sys.exit("You need to install prompt_toolkit to use the REPL client.")

    sock_path = find_sockfile()

    async with AsyncClient(sock_path) as client:
        reply = await client.repl_start()
        if not reply.status == IPCStatus.SUCCESS:
            sys.exit("Could not connect to REPL server.")

        session_id = reply.data["session_id"]
        welcome_message = reply.data["output"]

        class AsyncSocketCompleter(Completer):
            def __init__(self, client, session_id):
                self.client = client
                self.session_id = session_id

            def get_completions(self, document, complete_event):
                # Fallback required by Python's abstract base class check
                return
                yield

            async def get_completions_async(self, document, _complete_event):
                text_before_cursor = document.text_before_cursor
                match = re.search(r"([\w\.]+)$", text_before_cursor)
                if not match:
                    return

                word = match.group(1)
                start_position = -len(word)

                reply = await self.client.repl_request(self.session_id, {"completion": word})
                matches = reply.data.get("matches", [])
                options = list(filter(None, matches))
                if not options:
                    return

                for opt in options:
                    yield Completion(opt, start_position=start_position)

        kb = KeyBindings()
        completer = AsyncSocketCompleter(client, session_id)

        session = PromptSession(
            completer=completer,
            key_bindings=kb,
            complete_while_typing=False,
            multiline=True,
            prompt_continuation=lambda *args, **kwargs: "... ",
            history=InMemoryHistory(),
        )

        @kb.add("enter")
        async def _(event):
            buffer = event.app.current_buffer
            text = buffer.document.text

            if is_code_complete(text):
                reply = await client.repl_request(session_id, {"code": text})
                response = reply.data["output"]

                session.history.append_string(text)
                buffer.reset()

                text = text.replace("\n", "\n... ")
                print(f">>> {text}")
                if response.strip():
                    print(response, end="\n", flush=True)
            else:
                buffer.insert_text("\n")

        with patch_stdout():
            print(welcome_message, end="", flush=True)

            try:
                # Inner try...finally ensures repl_stop is called before
                # AsyncClient's __aexit__ tears down the stream.
                try:
                    while True:
                        await session.prompt_async(">>> ")
                finally:
                    await client.repl_stop(session_id)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")


def start_repl(args):
    try:
        asyncio.run(start_repl_async(args))
    except KeyboardInterrupt:
        pass


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser("repl", parents=parents, help="Run a qtile REPL session.")
    parser.set_defaults(func=start_repl)
