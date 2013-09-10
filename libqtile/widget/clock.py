from time import time
from datetime import datetime, timedelta
import calendar

from libqtile import bar
import base

import gobject

# for the popup window
from libqtile import notify_window
from textbox import TextBox
import pango


class Clock(base._TextBox):
    """
        A simple but flexible text-based clock, with ability to display 
        the current month calendar when the mouse is over the widget.
    """
    def __init__(self, fmt="%H:%M", width=bar.CALCULATED, **config):
        """
            - fmt: A Python datetime format string.

            - width: A fixed width, or bar.CALCULATED to calculate the width
            automatically (which is recommended).
        """
        base._TextBox.__init__(self, " ", width, **config)
        self.fmt = fmt
        self.configured = False
        self.popup = None


    def _configure(self, qtile, bar):
        if not self.configured:
            self.configured = True
            gobject.idle_add(self.update)
        base._TextBox._configure(self, qtile, bar)


    def update(self):
        """ action automatically called to update the time displayed """
        ts = time()

        self.timeout_add(1. - ts % 1., self.update)

        old_layout_width = self.layout.width

        # adding .5 to get a proper seconds value because glib could
        # theoreticaly call our method too early and we could get something
        # like (x-1).999 instead of x.000
        self.text = datetime.fromtimestamp(int(ts + .5)).strftime(self.fmt)

        if self.layout.width != old_layout_width:
            self.bar.draw()
        else:
            self.draw()

        return False


    def pointer_over(self, x, y, detail):
        """ action to do if the mouse if over the widget: display a calendar """
        if not self.popup:
            # clean if there are some popups form other widget alive
            for w in self.bar.popup_window.keys():
                w.leave_window(x, y, detail)

            # create the calendar popup window
            self.today = datetime.today()
            w = TextBox(calendar.month(self.today.year, self.today.month), fontsize=self.fontsize, font="monospace")
            self.popup = notify_window.NotifyWindow(self, [w])

            # save the popup window in the bar in case of the mouse
            # leave the widget to another widget in the bar
            self.bar.popup_window[self] = self.popup
            
            self.popup._configure(self.qtile, self.bar.screen)
            w.layout.layout.set_alignment(pango.ALIGN_LEFT)


    def leave_window(self, x, y, detail):
        """ action to proceed if the mouse leave the widget: kill the popup """
        if self.popup:
            self.popup.window.hide()
            self.popup.window.kill()
            self.popup.window = None
            self.popup = None
            self.bar.popup_window.pop(self)


    def newMonth(self, date, way):
        """
        return a date in the previous or next month
        @date: current date to move from
        @way: direction (-1/+1) to move
        """
        if date.day < 15:
            if way > 0:
                date = date + timedelta(33)
            else:
                date = date - timedelta(18)
        else:
            if way > 0:
                date = date + timedelta(18)
            else:
                date = date - timedelta(33)
        return date



    def button_press(self, x, y, button):
        """ 
        Two actions of modifying the calendar date are defined in case
        of button press on the widget
        """
        if self.today:
            if button == 1:
                # leftmost button: prev month
                self.today = self.newMonth(self.today, -1)
            elif button == 3:
                # rightmost button: next month
                self.today = self.newMonth(self.today, 1)
            self.popup.widgets[0].text = calendar.month(self.today.year, self.today.month)
            self.popup.draw()
