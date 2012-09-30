from groupbox import GroupBox
from groupbox import AGroupBox
from windowname import WindowName
from textbox import TextBox
from spacer import Spacer
from battery import Battery
from clock import Clock
from sep import Sep
from prompt import Prompt
from systray import Systray
from graph import *
try:
    from mpriswidget import Mpris
except ImportError:
    pass
try:
    from mpdwidget import Mpd
except ImportError:
    pass
from maildir import Maildir
from volume import Volume
from currentlayout import CurrentLayout

try:
    from yahoo_weather import YahooWeather
except ImportError:
    # Requires Python >= 2.6 or simplejson
    pass
from sensors import ThermalSensor
try:
    from wlan import Wlan
except ImportError:
    # Requires python-wifi
    pass
