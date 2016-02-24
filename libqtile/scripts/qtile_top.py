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

import os
import time
import argparse

import curses

import linecache
import tracemalloc
from tracemalloc import Snapshot
from libqtile import command


class TraceNotStarted(Exception):
    pass


class TraceCantStart(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(description="Top like for qtile")
    parser.add_argument('-l', '--lines', type=int, dest="lines", default=10,
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

    opts = parser.parse_args()
    return opts


def get_trace(client, force_start):
    (started, path) = client.tracemalloc_dump()
    if force_start and not started:
        client.tracemalloc_toggle()
        (started, path) = client.tracemalloc_dump()
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


def get_stats(scr, client, group_by='lineno', limit=10, seconds=1.5,
              force_start=False):
    (max_y, max_x) = scr.getmaxyx()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    while True:
        scr.addstr(0, 0, "Qtile - Top %s lines" % limit)
        scr.addstr(1, 0, '%-3s %-40s %-30s %-16s' % (
            '#', 'Line', 'Memory', ' ' * (max_x - 71)),
            curses.A_BOLD | curses.A_REVERSE)

        snapshot = get_trace(client, force_start)
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
            mem = "%.1f KiB" % (stat.size / 1024)
            filename = "%s:%s" % (filename, frame.lineno)
            scr.addstr(cnt + 1, 0, '%-3s %-40s %-30s' % (index, filename, mem))
            scr.addstr(cnt + 2, 4, code, curses.color_pair(1))
            cnt += 2

        other = top_stats[limit:]
        cnt += 2
        if other:
            size = sum(stat.size for stat in other)
            other_size = ("%s other: %.1f KiB" % (len(other), size / 1024))
            scr.addstr(cnt, 0, other_size, curses.A_BOLD)
            cnt += 1

        total = sum(stat.size for stat in top_stats)
        total_size = "Total allocated size: %.1f KiB" % (total / 1024)
        scr.addstr(cnt, 0, total_size, curses.A_BOLD)

        scr.move(max_y - 2, max_y - 2)
        scr.refresh()
        time.sleep(seconds)
        scr.erase()


def raw_stats(client, group_by='lineno', limit=10, force_start=False):
    snapshot = get_trace(client, force_start)
    snapshot = filter_snapshot(snapshot)
    top_stats = snapshot.statistics(group_by)

    print("Qtile - Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print("#%s: %s:%s: %.1f KiB"
              % (index, filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def main():
    opts = parse_args()
    lines = opts.lines
    seconds = opts.seconds
    force_start = opts.force_start
    client = command.Client(opts.socket)

    try:
        if not opts.raw:
            curses.wrapper(get_stats, client, limit=lines, seconds=seconds,
                           force_start=force_start)
        else:
            raw_stats(client, limit=lines, force_start=force_start)
    except TraceNotStarted:
        print("tracemalloc not started on qtile, start by setting "
              "PYTHONTRACEMALLOC=1 before starting qtile")
        print("or force start tracemalloc now, but you'll lose early traces")
        exit(1)
    except TraceCantStart:
        print("Can't start tracemalloc on qtile, check the logs")
    except KeyboardInterrupt:
        exit(-1)
