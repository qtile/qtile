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

from libqtile.utils import lazify_imports
from libqtile.widget.import_error import make_error

widgets = {
    "AGroupBox": "groupbox",
    "Backlight": "backlight",
    "Battery": "battery",
    "BatteryIcon": "battery",
    "Bluetooth": "bluetooth",
    "CPU": "cpu",
    "CPUGraph": "graph",
    "Canto": "canto",
    "CapsNumLockIndicator": "caps_num_lock_indicator",
    "CheckUpdates": "check_updates",
    "Chord": "chord",
    "Clipboard": "clipboard",
    "Clock": "clock",
    "Cmus": "cmus",
    "Countdown": "countdown",
    "CryptoTicker": "crypto_ticker",
    "CurrentLayout": "currentlayout",
    "CurrentScreen": "currentscreen",
    "DF": "df",
    "DoNotDisturb": "do_not_disturb",
    "GenPollText": "generic_poll_text",
    "GenPollUrl": "generic_poll_text",
    "GenPollCommand": "generic_poll_text",
    "GmailChecker": "gmail_checker",
    "GroupBox": "groupbox",
    "HDD": "hdd",
    "HDDBusyGraph": "graph",
    "HDDGraph": "graph",
    "IdleRPG": "idlerpg",
    "Image": "image",
    "ImapWidget": "imapwidget",
    "KeyboardKbdd": "keyboardkbdd",
    "KeyboardLayout": "keyboardlayout",
    "KhalCalendar": "khal_calendar",
    "LaunchBar": "launchbar",
    "Load": "load",
    "Maildir": "maildir",
    "Memory": "memory",
    "MemoryGraph": "graph",
    "Mirror": "base",
    "Moc": "moc",
    "Mpd2": "mpd2widget",
    "Mpris2": "mpris2widget",
    "Net": "net",
    "NetGraph": "graph",
    "NetUP": "netup",
    "Notify": "notify",
    "NvidiaSensors": "nvidia_sensors",
    "OpenWeather": "open_weather",
    "Plasma": "plasma",
    "Pomodoro": "pomodoro",
    "Prompt": "prompt",
    "PulseVolume": "pulse_volume",
    "QuickExit": "quick_exit",
    "Redshift": "redshift",
    "ScreenSplit": "screensplit",
    "Sep": "sep",
    "She": "she",
    "Spacer": "spacer",
    "StatusNotifier": "statusnotifier",
    "StockTicker": "stock_ticker",
    "SwapGraph": "graph",
    "SwayNC": "swaync",
    "Systray": "systray",
    "TaskList": "tasklist",
    "TextBox": "textbox",
    "ThermalSensor": "sensors",
    "ThermalZone": "thermal_zone",
    "TunedManager": "tuned_manager",
    "VerticalClock": "vertical_clock",
    "Volume": "volume",
    "Wallpaper": "wallpaper",
    "WidgetBox": "widgetbox",
    "WindowCount": "window_count",
    "WindowName": "windowname",
    "WindowTabs": "windowtabs",
    "Wlan": "wlan",
    "Wttr": "wttr",
}

__all__, __dir__, __getattr__ = lazify_imports(widgets, __package__, fallback=make_error)
