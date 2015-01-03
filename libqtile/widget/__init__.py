import logging
import traceback
import importlib


logger = logging.getLogger('qtile')


def safe_import(module_name, class_name):
    """
    try to import a module, and if it fails because an ImporError
    it logs on WARNING, and logs the traceback on DEBUG level
    """
    if type(class_name) is list:
        for name in class_name:
            safe_import(module_name, name)
        return
    package = __package__
    # python 3.2 don't set __package__
    if not package:
        package = __name__
    try:
        module = importlib.import_module(module_name, package)
        globals()[class_name] = getattr(module, class_name)
    except ImportError as error:
        msg = "Can't Import Widget: '%s.%s', %s"
        logger.warn(msg % (module_name, class_name, error))
        logger.debug(traceback.format_exc())


safe_import(".backlight", "Backlight")
safe_import(".battery", ["Battery", "BatteryIcon"])
safe_import(".clock", "Clock")
safe_import(".currentlayout", "CurrentLayout")
safe_import(".debuginfo", "DebugInfo")
safe_import(".graph", ["CPUGraph", "MemoryGraph", "SwapGraph", "NetGraph",
                       "HDDGraph", "HDDBusyGraph"])
safe_import(".groupbox", ["AGroupBox", "GroupBox"])
safe_import(".maildir", "Maildir")
safe_import(".notify", "Notify")
safe_import(".prompt", "Prompt")
safe_import(".sensors", "ThermalSensor")
safe_import(".sep", "Sep")
safe_import(".she", "She")
safe_import(".spacer", "Spacer")
safe_import(".systray", "Systray")
safe_import(".textbox", "TextBox")
safe_import(".volume", "Volume")
safe_import(".windowname", "WindowName")
safe_import(".windowtabs", "WindowTabs")
safe_import(".keyboardlayout", "KeyboardLayout")
safe_import(".df", "DF")
safe_import(".image", "Image")
safe_import(".gmail_checker", "GmailChecker")
safe_import(".clipboard", "Clipboard")
safe_import(".countdown", "Countdown")
safe_import(".tasklist", "TaskList")
safe_import(".pacman", "Pacman")
safe_import(".launchbar", "LaunchBar")
safe_import(".canto", "Canto")
safe_import(".mpriswidget", "Mpris")
safe_import(".mpris2widget", "Mpris2")
safe_import(".mpdwidget", "Mpd")
safe_import(".yahoo_weather", "YahooWeather")
safe_import(".bitcoin_ticker", "BitcoinTicker")
safe_import(".wlan", "Wlan")
safe_import(".google_calendar", "GoogleCalendar")
safe_import(".imapwidget", "ImapWidget")
safe_import(".net", "Net")
