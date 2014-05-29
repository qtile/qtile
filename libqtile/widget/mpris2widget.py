import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gobject

import base
from .. import bar

class Mpris2(base._TextBox):
    '''
    A widget which displays the current track/artist of your favorite MPRIS
    player. It should work with all MPRIS 2 compatible players
    which implement a reasonably correct version of MPRIS,
    though I have only tested it with audacious.
    '''
    defaults = [
                ('name', 'audacious', 'Name of the MPRIS widget.'),

                ('objname', 'org.mpris.MediaPlayer2.audacious',
                    'DBUS MPRIS 2 compatible player identifier'
                    '- Find it out with dbus-monitor - '
                    'Also see: http://specifications.freedesktop.org/'
                    'mpris-spec/latest/#Bus-Name-Policy'),

                ('display_metadata', ['xesam:title', 'xesam:album', 'xesam:artist'],
                     'Which metadata identifiers to display.'),

                ('scroll_chars', 30, 'How many chars at once to display.'),
                ('scroll_interval', 0.5, 'Scroll delay interval.'),
                ('scroll_wait_intervals', 8, 'Wait x scroll_interval before'
                     'scrolling/removing text'),
       ]

    def __init__(self, **config):
        base._TextBox.__init__(self, '', **config)
        self.add_defaults(self.__class__.defaults)

        dbus_loop = DBusGMainLoop()
        bus = dbus.SessionBus(mainloop=dbus_loop)
        bus.add_signal_receiver(self.update, 'PropertiesChanged',
            'org.freedesktop.DBus.Properties', self.objname,
            '/org/mpris/MediaPlayer2')

        self.scrolltext = None
        self.displaytext = ''
        self.is_playing = False
        self.scroll_timer = None
        self.scroll_counter = None

    def update(self, interface_name, changed_properties, invalidated_properties):
        '''http://specifications.freedesktop.org/
        mpris-spec/latest/Track_List_Interface.html#Mapping:Metadata_Map'''
        if not self.configured:
            return True
        olddisplaytext = self.displaytext
        self.displaytext = ''

        metadata = None
        playbackstatus = None
        metadata = changed_properties.get('Metadata', None)
        playbackstatus = changed_properties.get('PlaybackStatus', None)
        if metadata:
            self.is_playing = True
            self.displaytext = ' - '.join([metadata.get(x)
                          if isinstance(metadata.get(x), dbus.String)
                          else ' + '.join([y for y in metadata.get(x)
                          if isinstance(y, dbus.String)])
                          for x in self.display_metadata if metadata.get(x)])
            self.displaytext.replace('\n', '')
        if playbackstatus:
            if playbackstatus == 'Paused' and  olddisplaytext:
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
                self.playbackstatus = True
            else:
                self.is_playing = False
                self.displaytext = ''

        if self.scroll_chars and self.scroll_interval:
            if(self.scroll_timer):
                gobject.source_remove(self.scroll_timer)
            self.scrolltext = self.displaytext
            self.scroll_counter = self.scroll_wait_intervals
            self.scroll_timer = self.timeout_add(self.scroll_interval,
                    self.scroll_text)
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
                return True
        if len(self.scrolltext) >= self.scroll_chars:
            self.scrolltext = self.scrolltext[1:]
            if len(self.scrolltext) == self.scroll_chars:
                self.scroll_counter += self.scroll_wait_intervals
            return True
        self.text = ''
        self.bar.draw()
        return False

    def cmd_info(self):
        '''What's the current state of the widget?'''
        return dict(
            displaytext=self.displaytext,
            isplaying=self.is_playing,
        )
# vim: tabstop=4 shiftwidth=4 expandtab
