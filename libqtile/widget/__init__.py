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
