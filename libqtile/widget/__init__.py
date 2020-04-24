# Copyright (c) 2014 Rock Neurotiko
# Copyright (c) 2014 roger
# Copyright (c) 2015 David R. Andersen
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

from libqtile.log_utils import logger
from libqtile.utils import safe_import as safe_import_, time_call
# only directly import widgets that do not have any third party dependencies
# other than those required by qtile, otherwise use the same import function
from libqtile.widget.base import Mirror  # noqa: F401
from libqtile.widget.clock import Clock  # noqa: F401
from libqtile.widget.currentlayout import (  # noqa: F401
    CurrentLayout,
    CurrentLayoutIcon,
)
from libqtile.widget.groupbox import AGroupBox, GroupBox  # noqa: F401
from libqtile.widget.import_error import make_error
from libqtile.widget.prompt import Prompt  # noqa: F401
from libqtile.widget.quick_exit import QuickExit  # noqa: F401
from libqtile.widget.systray import Systray  # noqa: F401
from libqtile.widget.textbox import TextBox  # noqa: F401
from libqtile.widget.windowname import WindowName  # noqa: F401


LAZY_IMPORT_SPEC = {
    'backlight': ['Backlight'],
    'battery': ['Battery', 'BatteryIcon'],
    'currentscreen': ['CurrentScreen'],
    'debuginfo': ['DebugInfo'],
    'graph': ['CPUGraph',
              'MemoryGraph',
              'SwapGraph',
              'NetGraph',
              'HDDGraph',
              'HDDBusyGraph'],
    'maildir': ['Maildir'],
    'notify': ['Notify'],
    'sensors': ['ThermalSensor'],
    'sep': ['Sep'],
    'she': ['She'],
    'spacer': ['Spacer'],
    'generic_poll_text': ['GenPollText', 'GenPollUrl'],
    'volume': ['Volume'],
    'windowtabs': ['WindowTabs'],
    'keyboardlayout': ['KeyboardLayout'],
    'df': ['DF'],
    'image': ['Image'],
    'gmail_checker': ['GmailChecker'],
    'clipboard': ['Clipboard'],
    'countdown': ['Countdown'],
    'tasklist': ['TaskList'],
    'pacman': ['Pacman'],
    'launchbar': ['LaunchBar'],
    'canto': ['Canto'],
    'mpriswidget': ['Mpris'],
    'mpris2widget': ['Mpris2'],
    'mpd2widget': ['Mpd2'],
    'yahoo_weather': ['YahooWeather'],
    'bitcoin_ticker': ['BitcoinTicker'],
    'wlan': ['Wlan'],
    'khal_calendar': ['KhalCalendar'],
    'imapwidget': ['ImapWidget'],
    'net': ['Net'],
    'keyboardkbdd': ['KeyboardKbdd'],
    'cmus': ['Cmus'],
    'wallpaper': ['Wallpaper'],
    'check_updates': ['CheckUpdates'],
    'moc': ['Moc'],
    'memory': ['Memory'],
    'cpu': ['CPU'],
    'idlerpg': ['IdleRPG'],
    'pomodoro': ['Pomodoro'],
    'stock_ticker': ['StockTicker'],
    'caps_num_lock_indicator': ['CapsNumLockIndicator'],
    'quick_exit': ['QuickExit'],
    'pulse_volume': ['PulseVolume']
}


__all__ = list(set.union(*map(set, LAZY_IMPORT_SPEC.values())))


def safe_import(module_name, class_name):
    safe_import_(
        (".widget", module_name), class_name, globals(), fallback=make_error
    )


def __getattr__(name):
    module_name, class_names = None, None
    if name in __all__:
        for mod, names in LAZY_IMPORT_SPEC.items():
            if name in names:
                module_name, class_names = mod, names
                break
    if (module_name, class_names) != (None, None):
        # importing a single name does not improve performance
        # pass None because we want to handle the duration stuff (readability)
        _, duration = time_call(safe_import, None, module_name, class_names)
        if duration < 0.01:
            logger.debug('Attempt to safely import %s from .widget.%s took %.3f milliseconds',
                         class_names, module_name, duration * 1e3)
        else:
            log = (logger.debug if duration < 0.5
                   else logger.info if duration < 2
                   else logger.warning if duration < 60
                   else logger.error)
            log('Attempt to safely import %s from .widget.%s took %.3f seconds',
                class_names, module_name, duration)
        if name in globals():
            return globals()[name]
    raise AttributeError('module {!r} has no attribute {!r}'.format(__name__, name)) from None
