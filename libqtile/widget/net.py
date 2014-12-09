from . import base
import logging
import six

class Net(base.ThreadedPollText):

    """
        Displays interface down and up speed.
    """
    defaults = [
        ('interface', 'wlan0', 'The interface to monitor'),
        ('update_interval', 1, 'The update interval.'),
    ]

    def __init__(self, **config):
        base.ThreadedPollText.__init__(self, **config)
        self.add_defaults(Net.defaults)
        self.interfaces = self.get_stats()

    def convert_b(self, b):
        # Here we round to 1000 instead of 1024
        # because of round things
        letter = 'B'
        if b // 1000 > 0:
            b /= 1000.0
            letter = 'K'
        if b // 1000 > 0:
            b /= 1000.0
            letter = 'M'
        if b // 1000 > 0:
            b /= 1000.0
            letter = 'G'
        # I hope no one have more than 999 GB/s
        return b, letter

    def get_stats(self):
        lines = []  # type: List[str]
        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()[2:]
        interfaces = {}
        for s in lines:
            int_s = s.split()
            name = int_s[0][:-1]
            down = float(int_s[1])
            up = float(int_s[-8])
            interfaces[name] = {'down': down, 'up': up}
        return interfaces

    def _format(self, down, up):
        down = "%0.2f" % down
        up = "%0.2f" % up
        if len(down) > 5:
            down = down[:5]
        if len(up) > 5:
            up = up[:5]

        down = "  " * (5 - len(down)) + down
        up = "  " * (5 - len(up)) + up
        return down, up

    def poll(self):
        try:
            new_int = self.get_stats()
            down = new_int[self.interface]['down'] - \
                self.interfaces[self.interface]['down']
            up = new_int[self.interface]['up'] - \
                self.interfaces[self.interface]['up']

            down = down / self.update_interval
            up = up / self.update_interval
            down, down_letter = self.convert_b(down)
            up, up_letter = self.convert_b(up)

            down, up = self._format(down, up)

            str_base = six.u("%s%s \u2193\u2191 %s%s")

            self.interfaces = new_int
            return str_base % (down, down_letter, up, up_letter)
        except Exception as e:
            logging.getLogger('qtile').error('%s: Probably your wlan device is switched off or otherwise not present in your system.',
                                             self.__class__.__name__, str(e))
