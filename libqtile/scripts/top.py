# Copyright (c) 2015, Roger Duran
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

"""
    Command-line top like for qtile
"""

import curses
import linecache
import os
import sys
import time

from libqtile import ipc
from libqtile.command import client, interface

# These imports are here because they are not supported in pypy.
# having them at the top of the file causes problems when running any
# of the other scripts.
try:
    import tracemalloc
    from tracemalloc import Snapshot
    ENABLED = True
except ModuleNotFoundError:
    ENABLED = False


class TraceNotStarted(Exception):
    pass


class TraceCantStart(Exception):
    pass


def get_trace(c, force_start):
    (started, path) = c.tracemalloc_dump()
    if force_start and not started:
        c.tracemalloc_toggle()
        (started, path) = c.tracemalloc_dump()
        if not started:
            raise TraceCantStart
    elif not started:
        raise TraceNotStarted

    return Snapshot.load(path)


def filter_snapshot(snapshot):
    return snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))


def get_stats(scr, c, group_by='lineno', limit=10, seconds=1.5,
              force_start=False):
    (max_y, max_x) = scr.getmaxyx()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    while True:
        scr.addstr(0, 0, "Qtile - Top {} lines".format(limit))
        scr.addstr(1, 0, '{0:<3s} {1:<40s} {2:<30s} {3:<16s}'.format('#', 'Line', 'Memory', ' ' * (max_x - 71)),
                   curses.A_BOLD | curses.A_REVERSE)

        snapshot = get_trace(c, force_start)
        snapshot = filter_snapshot(snapshot)
        top_stats = snapshot.statistics(group_by)
        cnt = 1
        for index, stat in enumerate(top_stats[:limit], 1):
            frame = stat.traceback[0]
            # replace "/path/to/module/file.py" with "module/file.py"
            filename = os.sep.join(frame.filename.split(os.sep)[-2:])
            code = ""
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                code = line
            mem = "{:.1f} KiB".format(stat.size / 1024.0)
            filename = "{}:{}".format(filename, frame.lineno)
            scr.addstr(cnt + 1, 0, '{:<3} {:<40} {:<30}'.format(index, filename, mem))
            scr.addstr(cnt + 2, 4, code, curses.color_pair(1))
            cnt += 2

        other = top_stats[limit:]
        cnt += 2
        if other:
            size = sum(stat.size for stat in other)
            other_size = ("{:d} other: {:.1f} KiB".format(len(other), size / 1024.0))
            scr.addstr(cnt, 0, other_size, curses.A_BOLD)
            cnt += 1

        total = sum(stat.size for stat in top_stats)
        total_size = "Total allocated size: {0:.1f} KiB".format(total / 1024.0)
        scr.addstr(cnt, 0, total_size, curses.A_BOLD)

        scr.move(max_y - 2, max_y - 2)
        scr.refresh()
        time.sleep(seconds)
        scr.erase()


def raw_stats(c, group_by='lineno', limit=10, force_start=False):
    snapshot = get_trace(c, force_start)
    snapshot = filter_snapshot(snapshot)
    top_stats = snapshot.statistics(group_by)

    print("Qtile - Top {} lines".format(limit))
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print("#{}: {}:{}: {:.1f} KiB"
              .format(index, filename, frame.lineno, stat.size / 1024.0))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    {}'.format(line))

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("{:d} other: {:.1f} KiB".format(len(other), size / 1024.0))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: {0:.1f} KiB".format(total / 1024.0))


def top(opts):
    if not ENABLED:
        raise Exception('Could not import tracemalloc')
    lines = opts.lines
    seconds = opts.seconds
    force_start = opts.force_start
    if opts.socket is None:
        socket = ipc.find_sockfile()
    else:
        socket = opts.socket
    c = client.InteractiveCommandClient(
        interface.IPCCommandInterface(
            ipc.Client(socket),
        ),
    )

    try:
        if not opts.raw:
            curses.wrapper(get_stats, c, limit=lines, seconds=seconds,
                           force_start=force_start)
        else:
            raw_stats(c, limit=lines, force_start=force_start)
    except TraceNotStarted:
        print("tracemalloc not started on qtile, start by setting "
              "PYTHONTRACEMALLOC=1 before starting qtile")
        print("or force start tracemalloc now, but you'll lose early traces")
        sys.exit(1)
    except TraceCantStart:
        print("Can't start tracemalloc on qtile, check the logs")
    except KeyboardInterrupt:
        sys.exit(1)
    except curses.error:
        print("Terminal too small for curses interface.")
        raw_stats(c, limit=lines, force_start=force_start)


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser("top", parents=parents,
                                   help="resource usage information")
    parser.add_argument('-L', '--lines', type=int, dest="lines", default=10,
                        help='Number of lines.')
    parser.add_argument('-r', '--raw', dest="raw", action="store_true",
                        default=False, help='Output raw without curses')
    parser.add_argument('-t', '--time', type=float, dest="seconds",
                        default=1.5, help='Number of seconds to refresh')
    parser.add_argument('--force-start', dest="force_start",
                        action="store_true", default=False,
                        help='Force start tracemalloc on qtile')
    parser.add_argument('-s', '--socket', type=str, dest="socket",
                        help='Use specified communication socket.')
    parser.set_defaults(func=top)
