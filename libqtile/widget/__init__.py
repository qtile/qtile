from battery import Battery, BatteryIcon
from clock import Clock
from currentlayout import CurrentLayout
from graph import CPUGraph, MemoryGraph, SwapGraph, NetGraph, HDDGraph
from groupbox import AGroupBox, GroupBox
from maildir import Maildir
from notify import Notify
from prompt import Prompt
from sensors import ThermalSensor
from sep import Sep
from spacer import Spacer
from systray import Systray
from textbox import TextBox
from volume import Volume
from windowname import WindowName

try:
    from canto import Canto
except ImportError:
    pass

try:
    from mpriswidget import Mpris
except ImportError:
    pass

try:
    from mpdwidget import Mpd
except ImportError:
    pass

try:
    from yahoo_weather import YahooWeather
except ImportError:
    # Requires Python >= 2.6 or simplejson
    pass
