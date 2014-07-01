from backlight import Backlight
from battery import Battery, BatteryIcon
from clock import Clock
from currentlayout import CurrentLayout
from debuginfo import DebugInfo
from graph import CPUGraph, MemoryGraph, SwapGraph, NetGraph, HDDGraph, HDDBusyGraph
from groupbox import AGroupBox, GroupBox
from maildir import Maildir
from notify import Notify
from prompt import Prompt
from sensors import ThermalSensor
from sep import Sep
from she import She
from spacer import Spacer
from systray import Systray
from textbox import TextBox
from volume import Volume
from windowname import WindowName
from windowtabs import WindowTabs
from keyboardlayout import KeyboardLayout
from df import DF
from image import Image
from gmail_checker import GmailChecker

try:
    from launchbar import LaunchBar
except ImportError:
    pass

from tasklist import TaskList

try:
    from canto import Canto
except ImportError:
    pass

try:
    from mpriswidget import Mpris
except ImportError:
    pass

try:
    from mpris2widget import Mpris2
except ImportError:
    pass

try:
    from mpdwidget import Mpd
except ImportError:
    pass

try:
    from yahoo_weather import YahooWeather
    from bitcoin_ticker import BitcoinTicker
except ImportError:
    # Requires Python >= 2.6 or simplejson
    pass
from pacman import Pacman
try:
    from wlan import Wlan
except ImportError:
    # Requires python-wifi
    pass
try:
    from google_calendar import GoogleCalendar
except ImportError:
    pass
