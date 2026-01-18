from libqtile import ipc, sh
from libqtile.command import interface


def qshell(args) -> None:
    if args.socket is None:
        socket = ipc.find_sockfile()
    else:
        socket = args.socket
    client = ipc.Client(socket, is_json=args.is_json)
    cmd_object = interface.IPCCommandInterface(client)
    qsh = sh.QSh(cmd_object)
    if args.command is not None:
        qsh.process_line(args.command)
    else:
        qsh.loop()


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "shell", parents=parents, help="A shell-like interface to Qtile."
    )
    parser.add_argument(
        "-s",
        "--socket",
        action="store",
        type=str,
        default=None,
        help="Use specified socket for IPC.",
    )
    parser.add_argument(
        "-c",
        "--command",
        action="store",
        type=str,
        default=None,
        help="Run the specified qshell command and exit.",
    )
    parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        default=False,
        dest="is_json",
        help="Use JSON to communicate with Qtile.",
    )
    parser.set_defaults(func=qshell)
