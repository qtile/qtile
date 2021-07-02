# Copyright (c) 2021 elParaguayo
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

# NOTE: This test only tests the functionality of the widget and parts of the manager
# The notification service (in libqtile/notify.py) is tested separately
# TO DO: notification service test ;)

import shutil
import subprocess

import pytest

import libqtile.config
from libqtile.bar import Bar
from libqtile.widget import notify


# Bit of a hack... when we log a timer, save the delay in an attribute
# We'll use this to check message timeouts are being honoured.
def log_timeout(self, delay, func, method_args=None):
    self.delay = delay
    self.qtile.call_later(delay, func)


def notification(subject, body, urgency=None, timeout=None):
    '''Function to build notification text and command list'''
    cmds = []

    urgs = {0: "low", 1: "normal", 2: "critical"}
    urg_level = urgs.get(urgency, "normal")
    if urg_level != "normal":
        cmds += ["-u", urg_level]

    if timeout:
        cmds += ["-t", "{}".format(timeout)]

    cmds += [subject, body]

    text = '<span weight="bold">'
    if urg_level != "normal":
        text += '<span color="{{colour}}">'
    text += '{subject}'
    if urg_level != "normal":
        text += '</span>'
    text += '</span> - {body}'

    text = text.format(subject=subject, body=body)

    return text, cmds


# for Github CI/Ubuntu, "notify-send" is provided by libnotify-bin package
NS = shutil.which("notify-send")

URGENT = "#ff00ff"
LOW = "#cccccc"
DEFAULT_TIMEOUT = 3.0

MESSAGE_1, NOTIFICATION_1 = notification("Message 1",
                                         "Test Message 1",
                                         timeout=5000)
MESSAGE_2, NOTIFICATION_2 = notification("Urgent Message",
                                         "This is not a test!",
                                         urgency=2,
                                         timeout=10000)
MESSAGE_3, NOTIFICATION_3 = notification("Low priority",
                                         "Windows closed unexpectedly",
                                         urgency=0)


@pytest.mark.skipif(
    shutil.which("notify-send") is None,
    reason="notify-send not installed."
    )
@pytest.mark.usefixtures("dbus")
def test_notifications(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    notify.Notify.timeout_add = log_timeout
    widget = notify.Notify(foreground_urgent=URGENT,
                           foreground_low=LOW,
                           default_timeout=DEFAULT_TIMEOUT)
    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(
            top=Bar([widget], 10)
        )
    ]

    manager_nospawn.start(config)
    obj = manager_nospawn.c.widget["notify"]

    # Send first notification and check time and display time
    notif_1 = [NS]
    notif_1.extend(NOTIFICATION_1)
    subprocess.run(notif_1)
    assert obj.info()["text"] == MESSAGE_1

    _, timeout = obj.eval("self.delay")
    assert timeout == "5.0"

    # Send second notification and check time and display time
    notif_2 = [NS]
    notif_2.extend(NOTIFICATION_2)
    subprocess.run(notif_2)
    assert obj.info()["text"] == MESSAGE_2.format(colour=URGENT)

    _, timeout = obj.eval("self.delay")
    assert timeout == "10.0"

    # Send third notification and check time and display time
    notif_3 = [NS]
    notif_3.extend(NOTIFICATION_3)
    subprocess.run(notif_3)
    assert obj.info()["text"] == MESSAGE_3.format(colour=LOW)

    _, timeout = obj.eval("self.delay")
    assert timeout == str(DEFAULT_TIMEOUT)

    # Navigation tests

    # Hitting next while on last message should not change display
    obj.next()
    assert obj.info()["text"] == MESSAGE_3.format(colour=LOW)

    # Show previous
    obj.prev()
    assert obj.info()["text"] == MESSAGE_2.format(colour=URGENT)

    # Show previous
    obj.prev()
    assert obj.info()["text"] == MESSAGE_1

    # Show previous while on first message should stay on first
    obj.prev()
    assert obj.info()["text"] == MESSAGE_1

    # Show next
    obj.next()
    assert obj.info()["text"] == MESSAGE_2.format(colour=URGENT)

    # Toggle display (clear)
    obj.toggle()
    assert obj.info()["text"] == ""

    # Toggle display - restoring display shows last notification
    obj.toggle()
    assert obj.info()["text"] == MESSAGE_3.format(colour=LOW)

    # Clear the dispay
    obj.clear()
    assert obj.info()["text"] == ""

    # Show the display
    obj.display()
    assert obj.info()["text"] == MESSAGE_3.format(colour=LOW)
