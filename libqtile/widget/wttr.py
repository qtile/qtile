from urllib.parse import quote, urlencode

from libqtile.widget import GenPollUrl


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

    Add the character ``~`` at the beginning to get weather for some special
    location: ``~Vostok Station`` or ``~Eiffel Tower``.

    Also can use IP-addresses (direct) or domain names (prefixed with @) to
    specify a location:
    ``@github.com``, ``123.456.678.123``

    Specify multiple locations as dictionary ::

        location={
            'Minsk': 'Minsk',
            '64.127146,-21.873472': 'Reykjavik',
        }

    Cities will change randomly every update.
    """

    defaults = [
        (
            "format",
            "3",
            'Display text format. Choose presets in range 1-4 (Ex. ``"1"``) '
            "or build your own custom output format, use the special "
            "%-notation. See https://github.com/chubin/wttr.in#one-line-output",
        ),
        ("json", False, "Is Json?"),
        (
            "lang",
            "en",
            "Display text language. List of supported languages " "https://wttr.in/:translation",
        ),
        (
            "location",
            None,
            "Dictionary. Key is a city or place name, or GPS coordinates. "
            "Value is a display name.",
        ),
        (
            "units",
            "m",
            "``'m'`` - metric, ``'M'`` - show wind speed in m/s, "
            "``'u'`` - United States units",
        ),
        (
            "update_interval",
            600,
            "Update interval in seconds. Recommendation: if you want to "
            "display multiple locations alternately, maybe set a smaller "
            "interval, ex. ``30``.",
        ),
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, json=False, **config)
        self.add_defaults(Wttr.defaults)
        self.url = self._get_url()

    def _get_url(self):
        if not self.location:
            return None

        params = {
            "format": self.format,
            "lang": self.lang,
        }
        location = ":".join(quote(loc) for loc in self.location)
        url = f"https://wttr.in/{location}?{self.units}&{urlencode(params)}"
        return url

    def parse(self, response):
        for coord in self.location:
            response = response.strip().replace(coord, self.location[coord])
        return response
