# Copyright (c) 2014 Sebastian Kricner
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Tycho Andersen
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

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from libqtile.widget import base


class Mpris2(base._TextBox):
    """An MPRIS 2 widget

    A widget which displays the current track/artist of your favorite MPRIS
    player. It should work with all MPRIS 2 compatible players which implement
    a reasonably correct version of MPRIS, though I have only tested it with
    audacious.  This widget scrolls the text if neccessary and information that
    is displayed is configurable.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('name', 'audacious', 'Name of the MPRIS widget.'),

        ('objname', 'org.mpris.MediaPlayer2.audacious',
            'DBUS MPRIS 2 compatible player identifier'
            '- Find it out with dbus-monitor - '
            'Also see: http://specifications.freedesktop.org/'
            'mpris-spec/latest/#Bus-Name-Policy'),

        ('display_metadata', ['xesam:title', 'xesam:album', 'xesam:artist'],
            'Which metadata identifiers to display. '
            'See http://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/#index5h3 '
            'for available values'),

        ('scroll_chars', 30, 'How many chars at once to display.'),
        ('scroll_interval', 0.5, 'Scroll delay interval.'),
        ('scroll_wait_intervals', 8, 'Wait x scroll_interval before'
            'scrolling/removing text'),

        ('stop_pause_text', None, "Optional text to display when in the stopped/paused state"),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, '', **config)
        self.add_defaults(Mpris2.defaults)

        self.scrolltext = None
        self.displaytext = ''
        self.is_playing = False
        self.scroll_timer = None
        self.scroll_counter = None
        self.dbus_loop = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)

        # we don't need to reconnect all the dbus stuff if we already
        # connected it.
        if self.dbus_loop is not None:
            return

        # we need a main loop to get event signals
        # we just piggyback on qtile's main loop
        self.dbus_loop = DBusGMainLoop()
        self.bus = dbus.SessionBus(mainloop=self.dbus_loop)
        self.bus.add_signal_receiver(
            self.update, 'PropertiesChanged',
            'org.freedesktop.DBus.Properties', self.objname,
            '/org/mpris/MediaPlayer2'
        )

    def update(self, interface_name, changed_properties, invalidated_properties):
        """http://specifications.freedesktop.org/mpris-spec/latest/Track_List_Interface.html#Mapping:Metadata_Map"""
        if not self.configured:
            return True
        olddisplaytext = self.displaytext
        self.displaytext = ''

        metadata = None
        playbackstatus = None
        metadata = changed_properties.get('Metadata')
        playbackstatus = changed_properties.get('PlaybackStatus')
        if metadata:
            self.is_playing = True
            self.displaytext = ' - '.join([
                metadata.get(x)
                if isinstance(metadata.get(x), dbus.String)
                else ' + '.join(y for y in metadata.get(x) if isinstance(y, dbus.String))
                for x in self.display_metadata if metadata.get(x)
            ])
            self.displaytext.replace('\n', '')
        if playbackstatus:
            if playbackstatus == 'Paused' and self.stop_pause_text is not None:
                self.is_playing = False
                self.displaytext = self.stop_pause_text
            elif playbackstatus == 'Paused' and olddisplaytext:
                self.is_playing = False
                self.displaytext = 'Paused: {}'.format(olddisplaytext)
            elif playbackstatus == 'Paused':
                self.is_playing = False
                self.displaytext = 'Paused'
            elif playbackstatus == 'Playing' and not self.displaytext and \
                    olddisplaytext:
                self.is_playing = True
                self.displaytext = olddisplaytext.replace('Paused: ', '')
            elif playbackstatus == 'Playing' and not self.displaytext and \
                    not olddisplaytext:
                self.is_playing = True
                self.displaytext = 'No metadata for current track'
            elif playbackstatus == 'Playing' and self.displaytext:
                # Players might send more than one "Playing" message.
                pass
            else:
                self.is_playing = False
                self.displaytext = ''

        if self.scroll_chars and self.scroll_interval:
            if(self.scroll_timer):
                self.scroll_timer.cancel()
            self.scrolltext = self.displaytext
            self.scroll_counter = self.scroll_wait_intervals
            self.scroll_timer = self.timeout_add(self.scroll_interval, self.scroll_text)
            return
        if self.text != self.displaytext:
            self.text = self.displaytext
            self.bar.draw()

    def scroll_text(self):
        if self.text != self.scrolltext[:self.scroll_chars]:
            self.text = self.scrolltext[:self.scroll_chars]
            self.bar.draw()
        if self.scroll_counter:
            self.scroll_counter -= 1
            if self.scroll_counter:
                self.timeout_add(self.scroll_interval, self.scroll_text)
                return
        if len(self.scrolltext) >= self.scroll_chars:
            self.scrolltext = self.scrolltext[1:]
            if len(self.scrolltext) == self.scroll_chars:
                self.scroll_counter += self.scroll_wait_intervals
            self.timeout_add(self.scroll_interval, self.scroll_text)
            return
        self.text = ''
        self.bar.draw()

    def cmd_info(self):
        """What's the current state of the widget?"""
        return dict(
            displaytext=self.displaytext,
            isplaying=self.is_playing,
        )
