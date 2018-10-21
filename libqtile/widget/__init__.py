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

from ..utils import safe_import as safe_import_
from .import_error import make_error

from .clock import Clock  # noqa: F401
from .groupbox import AGroupBox, GroupBox  # noqa: F401
from .prompt import Prompt  # noqa: F401
from .systray import Systray  # noqa: F401
from .textbox import TextBox  # noqa: F401
from .windowname import WindowName  # noqa: F401


def safe_import(module_name, class_name):
    safe_import_((".widget", module_name), class_name, globals(),
                 fallback=make_error)


safe_import("backlight", "Backlight")
safe_import("battery", ["Battery", "BatteryIcon"])
safe_import("currentlayout", ["CurrentLayout", "CurrentLayoutIcon"])
safe_import("currentscreen", "CurrentScreen")
safe_import("debuginfo", "DebugInfo")
safe_import("graph", ["CPUGraph", "MemoryGraph", "SwapGraph", "NetGraph",
                      "HDDGraph", "HDDBusyGraph"])
safe_import("maildir", "Maildir")
safe_import("notify", "Notify")
safe_import("sensors", "ThermalSensor")
safe_import("sep", "Sep")
safe_import("she", "She")
safe_import("spacer", "Spacer")
safe_import("generic_poll_text", ["GenPollText", "GenPollUrl"])
safe_import("volume", "Volume")
safe_import("windowtabs", "WindowTabs")
safe_import("keyboardlayout", "KeyboardLayout")
safe_import("df", "DF")
safe_import("image", "Image")
safe_import("gmail_checker", "GmailChecker")
safe_import("clipboard", "Clipboard")
safe_import("countdown", "Countdown")
safe_import("tasklist", "TaskList")
safe_import("pacman", "Pacman")
safe_import("launchbar", "LaunchBar")
safe_import("canto", "Canto")
safe_import("mpriswidget", "Mpris")
safe_import("mpris2widget", "Mpris2")
safe_import("mpdwidget", "Mpd")
safe_import("mpd2widget", "Mpd2")
safe_import("yahoo_weather", "YahooWeather")
safe_import("bitcoin_ticker", "BitcoinTicker")
safe_import("wlan", "Wlan")
safe_import("khal_calendar", "KhalCalendar")
safe_import("imapwidget", "ImapWidget")
safe_import("net", "Net")
safe_import("keyboardkbdd", "KeyboardKbdd")
safe_import("cmus", "Cmus")
safe_import("wallpaper", "Wallpaper")
safe_import("check_updates", "CheckUpdates")
safe_import("moc", "Moc")
safe_import("memory", "Memory")
safe_import("idlerpg", "IdleRPG")
safe_import("pomodoro", "Pomodoro")
safe_import("stock_ticker", "StockTicker")
safe_import("dirty_memory", "DirtyMemory")
