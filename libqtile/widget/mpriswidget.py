import dbus
from dbus.mainloop.glib import DBusGMainLoop
import gobject

import base
from .. import bar

class Mpris(base._TextBox):
    ''''
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
                ('scroll_interval', 1, 'Scroll delay interval.'),
               ]

    def __init__(self, **config):
        super(self.__class__, self).__init__(self, **config)
        base._TextBox.__init__(self, '', **config)
        self.add_defaults(self.__class__.defaults)

        dbus_loop = DBusGMainLoop()
        bus = dbus.SessionBus(mainloop=dbus_loop)
        bus.add_signal_receiver(self.update, 'PropertiesChanged',
        'org.freedesktop.DBus.Properties', self.objname,
        '/org/mpris/MediaPlayer2')

        self.scrolltext = None
        self.playing = ''
        self.is_playing = False

    def update(self, *args):
        '''http://specifications.freedesktop.org/
        mpris-spec/latest/Track_List_Interface.html#Mapping:Metadata_Map'''
        if not self.configured:
            return True
        metadata = None
        playing = None
        playbackstatus = None
        for item in args:
            try:
                metadata = item.get('Metadata', None)
                playbackstatus = item.get('PlaybackStatus', None)
            except AttributeError:
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
        self.playing = playing if playing else ''
        if not self.scroll_chars or not self.scroll_interval:
            if self.text != playing:
                self.text = playing
                self.bar.draw()
        else:
            if(playing is not None):
                self.scrolltext = '{}{}{}'.format(' ' * self.scroll_chars,
                                        playing, ' ' * self.scroll_chars)
                self.timeout_add(self.scroll_interval, self.scroll_text)

    def scroll_text(self):
        if(self.scrolltext):
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
            nowplaying=self.playing,
            isplaying=self.is_playing,
        )
