from urllib.parse import quote, urlencode

from libqtile.widget import GenPollUrl, base


class Wttr(GenPollUrl):
    """Display weather widget provided by wttr.in_.

    .. _wttr.in: https://github.com/chubin/wttr.in/

    To specify your own custom output format, use the special %-notation
    (example: 'My_city: %t(%f), wind: %w'):

        - %c    Weather condition,
        - %C    Weather condition textual name,
        - %h    Humidity,
        - %t    Temperature (Actual),
        - %f    Temperature (Feels Like),
        - %w    Wind,
        - %l    Location,
        - %m    Moonphase 🌑🌒🌓🌔🌕🌖🌗🌘,
        - %M    Moonday,
        - %p    precipitation (mm),
        - %P    pressure (hPa),
        - %D    Dawn !,
        - %S    Sunrise !,
        - %z    Zenith !,
        - %s    Sunset !,
        - %d    Dusk !. (!times are shown in the local timezone)

    Specify multiple locations separated with ',': ``Minsk, Reykjavik``. Cities
    will change randomly every update.

    Add the character ``~`` at the beginning to get weather for some special
    location: ``~Vostok Station`` or ``~Eiffel Tower``.

    Also can use IP-addresses (direct) or domain names (prefixed with @) to
    specify a location:
    ``@github.com``, ``123.456.678.123``
    """

    orientation = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            'format', '3',
            'Display text format. Choose presets in range 1-4 (Ex. ``"1"``) '
            'or build your own custom output format, use the special '
            '%-notation. See https://github.com/chubin/wttr.in#one-line-output'
        ),
        (
            'lang', 'en',
            'Display text language. List of supported languages '
            'https://wttr.in/:translation'
        ),
        (
            'location', None,
            'City name or names of several cities separated by ``,``. This '
            'name will show if using ``%l`` in custom format.'
        ),
        (
            'units', 'm',
            "``'m'`` - metric, ``'M'`` - show wind speed in m/s, "
            "``'s'`` - imperial"
        ),
        (
            'update_interval', 600,
            'Update interval in seconds. Recommendation: if you want to '
            'display multiple locations alternately, maybe set a smaller '
            'interval, Ex. 30.'
        )
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, json=False, **config)
        self.add_defaults(Wttr.defaults)
        self.url = self._get_url()

    def _get_url(self):
        if not self.location:
            return None

        params = {
            'format': self.format,
            'lang': self.lang,
        }
        location = ":".join(
            quote(loc.strip()) for loc in self.location.split(",")
        )
        url = f'https://wttr.in/{location}?{self.units}&{urlencode(params)}'
        return url

    def parse(self, response):
        return response.strip()
