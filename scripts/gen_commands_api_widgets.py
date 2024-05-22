"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

widgets = [
    # Page name, page name, widget class.
    ("AGroupBox", "agroupbox.md", "libqtile.widget.AGroupBox"),
    ("Backlight", "backlight.md", "libqtile.widget.Backlight"),
    ("Battery", "battery.md", "libqtile.widget.Battery"),
    ("BatteryIcon", "batteryicon.md", "libqtile.widget.BatteryIcon"),
    ("Bluetooth", "bluetooth.md", "libqtile.widget.Bluetooth"),
    ("CPU", "cpu.md", "libqtile.widget.CPU"),
    ("CPUGraph", "cpugraph.md", "libqtile.widget.CPUGraph"),
    ("Canto", "canto.md", "libqtile.widget.Canto"),
    ("CapsNumLockIndicator", "capsnumlockindicator.md", "libqtile.widget.CapsNumLockIndicator"),
    ("CheckUpdates", "checkupdates.md", "libqtile.widget.CheckUpdates"),
    ("Chord", "chord.md", "libqtile.widget.Chord"),
    ("Clipboard", "clipboard.md", "libqtile.widget.Clipboard"),
    ("Clock", "clock.md", "libqtile.widget.Clock"),
    ("Cmus", "cmus.md", "libqtile.widget.Cmus"),
    ("Countdown", "countdown.md", "libqtile.widget.Countdown"),
    ("CryptoTicker", "cryptoticker.md", "libqtile.widget.CryptoTicker"),
    ("CurrentLayout", "currentlayout.md", "libqtile.widget.CurrentLayout"),
    ("CurrentLayoutIcon", "currentlayouticon.md", "libqtile.widget.CurrentLayoutIcon"),
    ("CurrentScreen", "currentscreen.md", "libqtile.widget.CurrentScreen"),
    ("DF", "df.md", "libqtile.widget.DF"),
    ("DoNotDisturb", "donotdisturb.md", "libqtile.widget.DoNotDisturb"),
    ("GenPollCommand", "genpollcommand.md", "libqtile.widget.GenPollCommand"),
    ("GenPollText", "genpolltext.md", "libqtile.widget.GenPollText"),
    ("GenPollUrl", "genpollurl.md", "libqtile.widget.GenPollUrl"),
    ("GmailChecker", "gmailchecker.md", "libqtile.widget.GmailChecker"),
    ("GroupBox", "groupbox.md", "libqtile.widget.GroupBox"),
    ("HDDBusyGraph", "hddbusygraph.md", "libqtile.widget.HDDBusyGraph"),
    ("HDDGraph", "hddgraph.md", "libqtile.widget.HDDGraph"),
    ("IdleRPG", "idlerpg.md", "libqtile.widget.IdleRPG"),
    ("Image", "image.md", "libqtile.widget.Image"),
    ("ImapWidget", "imapwidget.md", "libqtile.widget.ImapWidget"),
    ("KeyboardKbdd", "keyboardkbdd.md", "libqtile.widget.KeyboardKbdd"),
    ("KeyboardLayout", "keyboardlayout.md", "libqtile.widget.KeyboardLayout"),
    ("KhalCalendar", "khalcalendar.md", "libqtile.widget.KhalCalendar"),
    ("LaunchBar", "launchbar.md", "libqtile.widget.LaunchBar"),
    ("Load", "load.md", "libqtile.widget.Load"),
    ("Maildir", "maildir.md", "libqtile.widget.Maildir"),
    ("Memory", "memory.md", "libqtile.widget.Memory"),
    ("MemoryGraph", "memorygraph.md", "libqtile.widget.MemoryGraph"),
    ("Mirror", "mirror.md", "libqtile.widget.Mirror"),
    ("Moc", "moc.md", "libqtile.widget.Moc"),
    ("Mpd2", "mpd2.md", "libqtile.widget.Mpd2"),
    ("Mpris2", "mpris2.md", "libqtile.widget.Mpris2"),
    ("Net", "net.md", "libqtile.widget.Net"),
    ("NetGraph", "netgraph.md", "libqtile.widget.NetGraph"),
    ("Notify", "notify.md", "libqtile.widget.Notify"),
    ("NvidiaSensors", "nvidiasensors.md", "libqtile.widget.NvidiaSensors"),
    ("OpenWeather", "openweather.md", "libqtile.widget.OpenWeather"),
    ("Pomodoro", "pomodoro.md", "libqtile.widget.Pomodoro"),
    ("Prompt", "prompt.md", "libqtile.widget.Prompt"),
    ("PulseVolume", "pulsevolume.md", "libqtile.widget.PulseVolume"),
    ("QuickExit", "quickexit.md", "libqtile.widget.QuickExit"),
    ("ScreenSplit", "screensplit.md", "libqtile.widget.ScreenSplit"),
    ("Sep", "sep.md", "libqtile.widget.Sep"),
    ("She", "she.md", "libqtile.widget.She"),
    ("Spacer", "spacer.md", "libqtile.widget.Spacer"),
    ("StatusNotifier", "statusnotifier.md", "libqtile.widget.StatusNotifier"),
    ("StockTicker", "stockticker.md", "libqtile.widget.StockTicker"),
    ("SwapGraph", "swapgraph.md", "libqtile.widget.SwapGraph"),
    ("Systray", "systray.md", "libqtile.widget.Systray"),
    ("TaskList", "tasklist.md", "libqtile.widget.TaskList"),
    ("TextBox", "textbox.md", "libqtile.widget.TextBox"),
    ("ThermalSensor", "thermalsensor.md", "libqtile.widget.ThermalSensor"),
    ("ThermalZone", "thermalzone.md", "libqtile.widget.ThermalZone"),
    ("Volume", "volume.md", "libqtile.widget.Volume"),
    ("Wallpaper", "wallpaper.md", "libqtile.widget.Wallpaper"),
    ("WidgetBox", "widgetbox.md", "libqtile.widget.WidgetBox"),
    ("WindowCount", "windowcount.md", "libqtile.widget.WindowCount"),
    ("WindowName", "windowname.md", "libqtile.widget.WindowName"),
    ("WindowTabs", "windowtabs.md", "libqtile.widget.WindowTabs"),
    ("Wlan", "wlan.md", "libqtile.widget.Wlan"),
    ("Wttr", "wttr.md", "libqtile.widget.Wttr"),
]

for name, page, path in widgets:
    doc_path = Path("manual/commands/api/widgets", page)
    nav[name] = page
    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"---\ntitle: {name}\n---\n\n::: {path}\n    options:\n      commands: true\n")
    module_path = path.rsplit(".", 1)[0].replace(".", "/")
    mkdocs_gen_files.set_edit_path(doc_path, f"../{module_path}.py")

with mkdocs_gen_files.open("manual/commands/api/widgets/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
