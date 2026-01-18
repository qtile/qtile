import datetime
import string
import subprocess

import dateutil.parser

from libqtile.widget import base


class KhalCalendar(base.BackgroundPoll):
    """Khal calendar widget

    This widget will display the next appointment on your Khal calendar in the
    qtile status bar. Appointments within the "reminder" time will be
    highlighted.

    Widget requirements: dateutil_.

    .. _dateutil: https://pypi.org/project/python-dateutil/
    """

    defaults = [
        ("reminder_color", "FF0000", "color of calendar entries during reminder time"),
        ("foreground", "FFFF33", "default foreground color"),
        ("remindertime", 10, "reminder time in minutes"),
        ("lookahead", 7, "days to look ahead in the calendar"),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(KhalCalendar.defaults)
        self.text = "Calendar not initialized."
        self.default_foreground = self.foreground

    def poll(self):
        # get today and tomorrow
        now = datetime.datetime.now()
        # get reminder time in datetime format
        remtime = datetime.timedelta(minutes=self.remindertime)

        # parse khal output for the next seven days
        # and get the next event
        args = ["khal", "list", "now", str(self.lookahead) + "d"]
        cal = subprocess.Popen(args, stdout=subprocess.PIPE)
        output = cal.communicate()[0].decode("utf-8")
        if output == "No events\n":
            return "No appointments in next " + str(self.lookahead) + " days"
        output = output.split("\n")

        date = "unknown"
        starttime = None
        endtime = None

        # output[0] = 'Friday, 15/04/1976'
        outputsplitted = output[0].split(" ")
        date = outputsplitted[1]

        # output[1] = '[ ][12:00-13:00] dentist'
        try:
            output_nb = output[1].strip(" ")
            starttime = dateutil.parser.parse(date + " " + output_nb[:5], ignoretz=True)
            endtime = dateutil.parser.parse(date + " " + output_nb[6:11], ignoretz=True)
        except ValueError:
            # all day event output contains no start nor end time.
            starttime = dateutil.parser.parse(date + " 00:00", ignoretz=True)
            endtime = starttime + datetime.timedelta(hours=23, minutes=59)

        data = output[0].replace(",", "") + " " + output[1]

        # get rid of any garbage in appointment added by khal
        data = "".join(filter(lambda x: x in string.printable, data))
        # colorize the event if it is within reminder time
        if (starttime - remtime <= now) and (endtime > now):
            self.layout.colour = self.reminder_color
        else:
            self.layout.colour = self.default_foreground

        return data
