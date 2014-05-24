import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gobject

import base
from .. import bar

class Mpris(base._TextBox, object):
    ''''
    A widget which displays the current track/artist of your favorite MPRIS
    player. It should work with all players which implement a reasonably
    correct version of MPRIS, though I have only tested it with clementine.
    '''
    defaults = [
                ('name', 'audacious', 'Name of the MPRIS widget.'),
                ('objname', 'org.mpris.MediaPlayer2.audacious', 'DBUS MPRIS compatible player identifier - Find it out with dbus-monitor, grepping for RequestName'),
                ('display_metadata', ['xesam:title', 'xesam:album', 'xesam:artist'], 'Which metadata identifiers to display.'),
                ('scroll_chars', 30, 'How many chars to display. If too many it will scroll.'),
                ('scroll_interval', 1, 'Scroll delay interval.'),
               ]

    def __init__(self, **config):
        super(self.__class__, self).__init__(self, **config)
        base._TextBox.__init__(self, '', **config)
        self.add_defaults(self.__class__.defaults)

        dbus_loop = DBusGMainLoop()
        bus = dbus.SessionBus(mainloop=dbus_loop)
        bus.add_signal_receiver(self.update, 'PropertiesChanged',
        'org.freedesktop.DBus.Properties', 'org.mpris.MediaPlayer2.audacious',
        '/org/mpris/MediaPlayer2')

    def update(self, *args):
        if not self.configured:
            return True
        metadata = None
        playing = None
        playbackstatus = None
        try:
            metadata = args[1].get('Metadata', None)
            playbackstatus = args[1].get('PlaybackStatus', None)
        except IndexError as e:
            pass
        if(metadata):
            self.is_playing = True
            playing = ' - '.join([metadata.get(x)
                                  if isinstance(metadata.get(x), dbus.String)
                                  else ' + '.join(metadata.get(x))
                                  for x in self.display_metadata if metadata.get(x)])
        else:
            self.is_playing = False
            playing = ''
        if(playbackstatus):
            if playbackstatus == 'Playing' and not metadata and self.playing:
                self.is_playing = True
                playing = self.playing.lstrip('Paused: ')
            if playbackstatus == '':
                self.is_playing = False
                playing = playbackstatus
            if playbackstatus == 'Paused' and self.playing:
                self.is_playing = False
                playing = 'Paused: {}'.format(self.playing)
        self.playing = playing
        if not self.scroll_chars or not self.scroll_interval:
            if self.text != playing:
                self.text = playing
                self.bar.draw()
        else:
            if(playing):
                self.scrolltext = '{}{}{}'.format(' ' * self.scroll_chars, playing, ' ' * self.scroll_chars)
                self.timeout_add(self.scroll_interval, self.scroll_text)

    def scroll_text(self):
        if(getattr(self, 'scrolltext', None)):
            self.text = self.scrolltext[:self.scroll_chars]
            self.scrolltext = self.scrolltext[1:]
            self.bar.draw()
            return True
        self.text = ''
        self.bar.draw()
        return False

    def cmd_info(self):
        '''What's the current state of the widget?'''
        return dict(
            nowplaying=getattr(self, 'playing', ''),
            isplaying=getattr(self, 'is_playing', False),
        )
