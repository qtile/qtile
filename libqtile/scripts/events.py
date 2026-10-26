"""
``qtile events``: print the events published by a running qtile.

Connects to the event feed socket (see :mod:`libqtile.events`) and writes one
JSON object per line to stdout, so the output composes with ``jq``, ``grep``
and friends.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from typing import TYPE_CHECKING, NoReturn

from libqtile import ipc
from libqtile.events import PROTOCOL_VERSION

if TYPE_CHECKING:
    import argparse


def default_socket_path() -> str:
    """The event socket lives next to the IPC socket, with an ``.events`` suffix."""
    return ipc.find_sockfile() + ".events"


def error(message: str) -> NoReturn:
    print(f"qtile events: {message}", file=sys.stderr)
    sys.exit(1)


def split_events(values: list[str] | None) -> list[str]:
    """Accept both ``-e a -e b`` and ``-e a,b``."""
    names: list[str] = []
    for value in values or []:
        names.extend(n.strip() for n in value.split(",") if n.strip())
    return names


def connect(path: str) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(path)
    except FileNotFoundError:
        sock.close()
        error(f"no event socket at {path}. Is qtile running with the event feed enabled?")
    except ConnectionRefusedError:
        sock.close()
        error(f"connection refused on {path} (stale socket?)")
    except OSError as e:
        sock.close()
        error(f"cannot connect to {path}: {e}")
    return sock


def emit(message: dict, pretty: bool) -> bool:
    """Print a message. Returns False if stdout has been closed (e.g. ``| head``)."""
    try:
        print(json.dumps(message, indent=2 if pretty else None), flush=True)
    except BrokenPipeError:
        # Downstream closed the pipe. Not an error. Point stdout at devnull so
        # interpreter shutdown doesn't try to flush into the broken pipe.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return False
    return True


def qtile_events(args: argparse.Namespace) -> None:
    try:
        path = args.socket or default_socket_path()
    except ipc.IPCError as e:
        error(str(e))

    wanted = split_events(args.events)
    sock = connect(path)

    seen = 0
    try:
        with sock, sock.makefile("rw", encoding="utf-8", newline="\n") as stream:
            if wanted:
                try:
                    stream.write(json.dumps({"type": "subscribe", "events": wanted}) + "\n")
                    stream.flush()
                except OSError as e:
                    error(f"cannot send to qtile: {e}")

            for line in stream:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(msg, dict):
                    continue

                kind = msg.get("type")
                if kind == "hello":
                    version = msg.get("version")
                    if version != PROTOCOL_VERSION:
                        error(
                            f"server speaks event protocol version {version}, "
                            f"this client speaks {PROTOCOL_VERSION}"
                        )
                    if args.hello and not emit(msg, args.pretty):
                        return
                elif kind == "event":
                    # The server filters too, but events fired between connecting
                    # and the filter taking effect arrive unfiltered. Drop them here.
                    if wanted and msg.get("event") not in wanted:
                        continue
                    if not emit(msg, args.pretty):
                        return
                    seen += 1
                    if args.count and seen >= args.count:
                        return
                # Any other message type is from a newer server: ignore it.
            else:
                # Loop ended without break: the server closed the connection.
                error("connection closed by qtile")
    except KeyboardInterrupt:
        return


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
    parser.add_argument(
        "--hello",
        action="store_true",
        default=False,
        help="Also print the server's initial hello message.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        default=False,
        help="Indent the JSON output (one multi-line object per event).",
    )
    parser.set_defaults(func=qtile_events)
