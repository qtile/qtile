"""
``qtile events``: print the events published by a running qtile.

Connects to the event feed socket (see :mod:`libqtile.events`) and writes one
JSON object per line to stdout, so the output composes with ``jq``, ``grep``
and friends.
"""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING, NoReturn

from libqtile.ipc import (
    AsyncClient,
    IPCEventsNotifyMessage,
    IPCMessage,
    IPCStatus,
    find_sockfile,
)

if TYPE_CHECKING:
    import argparse


def error(message: str) -> NoReturn:
    print(f"qtile events: {message}", file=sys.stderr)
    sys.exit(1)


def split_events(values: list[str] | None) -> list[str]:
    """Accept both ``-e a -e b`` and ``-e a,b``."""
    names: list[str] = []
    for value in values or []:
        names.extend(n.strip() for n in value.split(",") if n.strip())
    return names


async def qtile_events(args: argparse.Namespace) -> None:
    count = 0
    path = args.socket or find_sockfile()

    # Event to signal when we want to exit gracefully
    exit_event = asyncio.Event()

    async with AsyncClient(path) as client:

        async def handle_message(message: IPCMessage):
            nonlocal count
            if isinstance(message, IPCEventsNotifyMessage):
                count += 1
                print(message.to_json())
                if args.count and count >= args.count:
                    await client.events_unsubscribe()
                    exit_event.set()

        wanted = split_events(args.events)
        try:
            msg = await client.events_subscribe(wanted, callback=handle_message)
            if msg.status != IPCStatus.SUCCESS:
                error("Could not subscribe to events.")

            client.start_listening(handle_message)

            # Keep the main function running in the background while
            # `_listen_loop` processes messages asynchronously.
            try:
                await exit_event.wait()
            except asyncio.CancelledError:
                pass

        except KeyboardInterrupt:
            pass

        await client.stop_listening()


def run(args):
    asyncio.run(qtile_events(args))


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "events",
        parents=parents,
        help="Stream events (hooks) from a running qtile as JSON lines.",
    )
    parser.add_argument(
        "-s",
        "--socket",
        action="store",
        type=str,
        default=None,
        help="Event socket to connect to. Defaults to the IPC socket path plus '.events'.",
    )
    parser.add_argument(
        "-e",
        "--event",
        action="append",
        dest="events",
        metavar="NAME",
        help="Only show this event. May be repeated or comma-separated. Default: all events.",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=0,
        metavar="N",
        help="Exit after N events (the hello message doesn't count).",
    )
    parser.set_defaults(func=run)
