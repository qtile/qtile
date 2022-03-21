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
import asyncio
import shutil
import subprocess
import textwrap

import pytest

import libqtile.config
from libqtile.bar import Bar
from libqtile.notify import notifier
from libqtile.widget import notify


# Bit of a hack... when we log a timer, save the delay in an attribute
# We'll use this to check message timeouts are being honoured.
def log_timeout(self, delay, func, method_args=None):
    self.delay = delay
    self.qtile.call_later(delay, func)


def notification(subject, body, urgency=None, timeout=None):
    """Function to build notification text and command list"""
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
    text += "{subject}"
    if urg_level != "normal":
        text += "</span>"
    text += "</span> - {body}"

    text = text.format(subject=subject, body=body)

    return text, cmds


# for Github CI/Ubuntu, "notify-send" is provided by libnotify-bin package
NS = shutil.which("notify-send")

URGENT = "#ff00ff"
LOW = "#cccccc"
DEFAULT_TIMEOUT = 3.0

MESSAGE_1, NOTIFICATION_1 = notification("Message 1", "Test Message 1", timeout=5000)
MESSAGE_2, NOTIFICATION_2 = notification(
    "Urgent Message", "This is not a test!", urgency=2, timeout=10000
)
MESSAGE_3, NOTIFICATION_3 = notification("Low priority", "Windows closed unexpectedly", urgency=0)


@pytest.mark.skipif(shutil.which("notify-send") is None, reason="notify-send not installed.")
@pytest.mark.usefixtures("dbus")
def test_notifications(manager_nospawn, minimal_conf_noscreen):
    notify.Notify.timeout_add = log_timeout
    widget = notify.Notify(
        foreground_urgent=URGENT, foreground_low=LOW, default_timeout=DEFAULT_TIMEOUT
    )
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([widget], 10))]

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


def test_capabilities():
    # Default capabilities are "body" and "actions"
    widget_with_actions = notify.Notify()
    assert widget_with_actions.capabilities == {"body", "actions"}

    # If the user chooses not to have actions, the capabilities
    # are adjusted accordingly
    widget_no_actions = notify.Notify(action=False)
    assert widget_no_actions.capabilities == {"body"}


@pytest.mark.skipif(shutil.which("notify-send") is None, reason="notify-send not installed.")
@pytest.mark.usefixtures("dbus")
def test_invoke_and_clear(manager_nospawn, minimal_conf_noscreen):

    # We need to create an object to listen for signals from the qtile
    # notification server. This needs to be created within the manager
    # object so we rely on "eval" applying "exec".
    handler = textwrap.dedent(
        """
        import asyncio

        from libqtile.utils import add_signal_receiver

        class SignalListener:
            def __init__(self):
                self.action_invoked = None
                self.notification_closed = None
                global add_signal_receiver
                global asyncio
                asyncio.create_task(
                    add_signal_receiver(
                        self.on_notification_closed,
                        session_bus=True,
                        signal_name="NotificationClosed"
                    )
                )

                asyncio.create_task(
                    add_signal_receiver(
                        self.on_action_invoked,
                        session_bus=True,
                        signal_name="ActionInvoked"
                    )
                )

            def on_action_invoked(self, msg):
                self.action_invoked = msg.body

            def on_notification_closed(self, msg):
                self.notification_closed = msg.body

        self.signal_listener = SignalListener()
        """
    )

    # Create and send a custom notification with a list of actions.
    # `utils.send_notfication` is not an option here as it does not
    # expose actions so we need a lower-level call
    notification_with_actions = textwrap.dedent(
        """
        import asyncio

        from dbus_next import Variant
        from dbus_next.constants import MessageType

        from libqtile.utils import _send_dbus_message

        notification = [
            "qtile",
            2,
            "",
            "Test",
            "Test with actions",
            ["default", "ok"],
            {"urgency": Variant("y", 1)},
            5000
        ]

        asyncio.create_task(
            _send_dbus_message(
                True,
                MessageType.METHOD_CALL,
                "org.freedesktop.Notifications",
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications",
                "Notify",
                "susssasa{sv}i",
                notification
            )
        )
        """
    )

    notify.Notify.timeout_add = log_timeout
    widget = notify.Notify()
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([widget], 10))]

    # Start the manager
    manager_nospawn.start(config)

    # Create our signal listener
    manager_nospawn.c.eval(handler)

    # Send first notification and check time and display time
    notif_1 = [NS]
    notif_1.extend(NOTIFICATION_1)
    subprocess.run(notif_1)

    # Check that listener hasn't received any signals yet
    _, result = manager_nospawn.c.eval("self.signal_listener.action_invoked")
    assert result == "None"

    _, result = manager_nospawn.c.eval("self.signal_listener.notification_closed")
    assert result == "None"

    # Clicking on notification dismisses it
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, button=1)

    # Signal listener should get the id and close reason
    # id is 1 and dismiss reason is ClosedReason.dismissed which is 2
    _, result = manager_nospawn.c.eval("self.signal_listener.notification_closed")
    assert result == "[1, 2]"

    # Send a new notification with defined actions
    _, res = manager_nospawn.c.eval(notification_with_actions)

    # Right-clicking on notification invokes it
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, button=3)

    # Signal listener should get the id and close reason
    # id is 2 (as it is the second notification) and action is "default"
    _, result = manager_nospawn.c.eval("self.signal_listener.action_invoked")
    assert result == "[2, 'default']"


@pytest.mark.skipif(shutil.which("notify-send") is None, reason="notify-send not installed.")
@pytest.mark.usefixtures("dbus")
def test_parse_text(manager_nospawn, minimal_conf_noscreen):
    def test_parser(text):
        return f"TEST:{text}"

    widget = notify.Notify(
        foreground_urgent=URGENT,
        foreground_low=LOW,
        default_timeout=DEFAULT_TIMEOUT,
        parse_text=test_parser,
    )
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([widget], 10))]

    manager_nospawn.start(config)
    obj = manager_nospawn.c.widget["notify"]

    # Send first notification and check time and display time
    notif_1 = [NS]
    notif_1.extend(NOTIFICATION_1)
    subprocess.run(notif_1)
    assert obj.info()["text"] == f"TEST:{MESSAGE_1}"


@pytest.mark.usefixtures("dbus")
def test_unregister():
    """Short test to check if notifier deregisters correctly."""

    async def deregister():
        def no_op(*args, **kwargs):
            pass

        do_nothing = no_op

        await notifier.register(no_op)
        await notifier.register(do_nothing)

        # Remove one callback: service will not be stopped
        task = notifier.unregister(no_op)
        assert task is None
        assert notifier._service

        # Remove last callback: service will now be stopped
        task = notifier.unregister(do_nothing)
        assert task
        await task
        assert notifier._service is None

    asyncio.run(deregister())
