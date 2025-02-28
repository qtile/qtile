import glob
import os
import shutil
import stat

MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH


def set_file_perms(p, options):
    try:
        os.chmod(p, MODE)
        shutil.chown(p, user=None, group=options.group)
    except FileNotFoundError:
        pass


def do_backlight_setup(options):
    set_file_perms(f"/sys/class/backlight/{options.device}/brightness", options)
    set_file_perms(f"/sys/class/leds/{options.device}/brightness", options)


def do_battery_setup(options):
    files = glob.glob("/sys/class/power_supply/BAT*/charge_control_*_threshold")
    for file in files:
        set_file_perms(file, options)


def udev(options):
    if options.kind == "backlight":
        do_backlight_setup(options)
    elif options.kind == "battery":
        do_battery_setup(options)
    else:
        raise f"Unknown udev option {options.kind}"


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser("udev", parents=parents)
    parser.add_argument("kind", choices=["backlight", "battery"])
    parser.add_argument("--device")
    parser.add_argument("--group", default="sudo")
    parser.set_defaults(func=udev)
