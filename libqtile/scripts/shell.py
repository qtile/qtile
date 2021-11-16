# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

from pathlib import Path
from typing import Optional

import typer

from libqtile import ipc, sh
from libqtile.command import interface


def shell(
    socket: Optional[Path] = typer.Option(None, "-s", "--socket", help="Path of the Qtile IPC socket."),
    command: Optional[str] = typer.Option(None, "-c", "--command", help="Run the specified shell command."),
    json: bool = typer.Option(False, "-j", "--json", help="Don't spawn apps (Used for restart)."),
) -> None:
    """
    A shell-like interface to Qtile.
    """
    if socket is None:
        socket = ipc.find_sockfile()
    client = ipc.Client(socket, is_json=json)
    cmd_object = interface.IPCCommandInterface(client)
    qsh = sh.QSh(cmd_object)
    if command:
        qsh.process_line(command)
    else:
        qsh.loop()
