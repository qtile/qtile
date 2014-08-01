Built-in Widgets
================


Applications
------------

BitcoinTicker
~~~~~~~~~~~~~

A bitcoin ticker widget, data provided by the btc-e.com API. Defaults to
displaying currency in whatever the current locale is.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - update_delay
      - ``600``
      - The delay in seconds between updates
    * - currency
      - defaults to current locale
      - The currency the value of bitcoin is displayed in'),
    * - format
      - ``"BTC Buy: {buy}, Sell: {sell}"``
      - Display format, available variables: buy, sell, high, low, avg, vol, vol_cur, last.


Canto
~~~~~

Display RSS feeds updates using the canto console reader.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - fetch
      - ``False``
      - Whether to fetch new items on update
    * - feeds
      - ``[]``
      - List of feeds to display, empty for all
    * - one_format
      - ``"{name}: {number}"``
      - One feed display format
    * - all_format
      - ``"{number}"``
      - All feeds display format
    * - update_delay
      - ``600``
      - The delay in seconds between updates

GmailChecker
~~~~~~~~~~~~

A simple gmail checker.
You will need to write your Gmail password into to your config to use this widget.
Decide for yourself if this is a good idea.

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - username
      - ``None``
      - Gmail username i.e. email@gmail.com
    * - password
      - ``None``
      - Your Gmail password.
    * - email_path
      - ``None``
      - valid email path
    * - fmt'
      - ``"inbox[%s],unseen[%s]"``
      - format string fot textbox widget
    * - status_only_unseen
      - ``False``
      - only show unseen mail count



GoogleCalendar
~~~~~~~~~~~~~~

This widget will display the next appointment on your Google calendar
in the qtile status bar. Appointments within the "reminder" time will
be highlighted. Authentication credentials are stored in a file on
disk.

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - calendar
      - ``"primary"ä``
      - calendar to use
    * - format'
      - ``" {next_event} "``
      - text to display - leave this at the default for now...
    * - storage_file
      - ``None``
      - absolute path of secrets file - must be set
    * - reminder_color
      - ``"FF0000"``
      - color of calendar entries during reminder time
    * - www_group
      - ``"www"``
      - group to open browser into
    * - www_screen
      - ``0``
      - screen to open group on
    * - browser_cmd
      - ``"/usr/bin/firefox -url calendar.google.com"``
      - command or script to execute on click


Maildir
~~~~~~~

A simple widget showing the number of new mails in maildir mailboxes.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Maildir widget font size. Calculated if None.
    * - padding
      - ``None``
      - Maildir widget padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - maildirPath
      - ``"~/Mail"``
      - path to the Maildir folder"
    * - subFolders
      - ``[]``
      - The subfolders to scan (e.g. [{"path": "INBOX", "label": "Home mail"}, {"path": "spam", "label": "Home junk"}])
    * - separator
      - ``" "``
      - the string to put between the subfolder strings.


Mpris
~~~~~

A widget which displays the current track/artist of your favorite MPRIS
player. It should work with all players which implement a reasonably
correct version of MPRIS, though I have only tested it with clementine.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - widget font
    * - fontsize
      - ``None``
      - widget pixel size. Calculated if None.
    * - padding
      - ``None``
      - widget padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour


YahooWeather
~~~~~~~~~~~~

A weather widget, data provided by the Yahoo! Weather API

Format options:

* astronomy_sunrise
* astronomy_sunset
* atmosphere_humidity
* atmosphere_visibility
* atmosphere_pressure
* atmosphere_rising
* condition_text
* condition_code
* condition_temp
* condition_date
* location_city
* location_region
* location_country
* units_temperature
* units_distance
* units_pressure
* units_speed
* wind_chill
* wind_direction
* wind_speed

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size, calculated if None.
    * - padding
      - ``None``
      - Padding, calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - location
      - ``None``
      - Location to fetch weather for. Ignored if woeid is set.
    * - woeid
      - ``None``
      - Where On Earth ID. Auto-calculated if location is set.
    * - format
      - ``"{location_city}: {condition_temp} °{units_temperature}"``
      - Display format
    * - metric
      - ``True``
      - True to use metric/C, False to use imperial/F
    * - update_interval
      - ``600``
      - Update interval in seconds


Graphs
------


.. image:: /_static/widgets/graph.png


CPUGraph
~~~~~~~~

Display a CPU usage graph.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - graph_color
      - ``"18BAEB"``
      - Graph color
    * - fill_color
      - ``"1667EB.3"``
      - Fill color for linefill graph
    * - background
      - ``"000000"``
      - Widget background
    * - border_color
      - ``"215578"``
      - Widget border color
    * - border_width
      - ``2``
      - Widget background
    * - margin_x
      - ``3``
      - Margin X
    * - margin_y
      - ``3``
      - Margin Y
    * - samples
      - ``100``
      - Count of graph samples.
    * - frequency
      - ``1``
      - Update frequency in seconds
    * - type
      - ``"linefill"``
      - 'box', 'line', 'linefill'
    * - line_width
      - ``3``
      - Line width
    * - start_pos
      - ``"bottom"``
      - Drawer starting position ('bottom'/'top')
    * - core
      - ``"all"``
      - Which core to show (all/0/1/2/...)


HDDBusyGraph
~~~~~~~~~~~~

Display a HDD usage stats graph.
Parses /sys/block/<dev>/stat file and extracts overall device
IO usage, based on `io_ticks`'s value.
See https://www.kernel.org/doc/Documentation/block/stat.txt

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - graph_color
      - ``"18BAEB"``
      - Graph color
    * - fill_color
      - ``"1667EB.3"``
      - Fill color for linefill graph
    * - background
      - ``"000000"``
      - Widget background
    * - border_color
      - ``"215578"``
      - Widget border color
    * - border_width
      - ``2``
      - Widget background
    * - margin_x
      - ``3``
      - Margin X
    * - margin_y
      - ``3``
      - Margin Y
    * - samples
      - ``100``
      - Count of graph samples.
    * - frequency
      - ``60``
      - Update frequency in seconds
    * - type
      - ``"linefill"``
      - 'box', 'line', 'linefill'
    * - line_width
      - ``3``
      - Line width
    * - start_pos
      - ``"bottom"``
      - Drawer starting position ('bottom'/'top')
    * - device
      - ``"sda"``
      - Block device to display info for.

HDDGraph
~~~~~~~~

Display HDD free or used space graph.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - graph_color
      - ``"18BAEB"``
      - Graph color
    * - fill_color
      - ``"1667EB.3"``
      - Fill color for linefill graph
    * - background
      - ``"000000"``
      - Widget background
    * - border_color
      - ``"215578"``
      - Widget border color
    * - border_width
      - ``2``
      - Widget background
    * - margin_x
      - ``3``
      - Margin X
    * - margin_y
      - ``3``
      - Margin Y
    * - samples
      - ``100``
      - Count of graph samples.
    * - frequency
      - ``60``
      - Update frequency in seconds
    * - type
      - ``"linefill"``
      - 'box', 'line', 'linefill'
    * - line_width
      - ``3``
      - Line width
    * - start_pos
      - ``"bottom"``
      - Drawer starting position ('bottom'/'top')
    * - path
      - ``"/"``
      - Partition mount point.
    * - space_type
      - ``"used"``
      - free/used


MemoryGraph
~~~~~~~~~~~

Displays a memory usage graph.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - graph_color
      - ``"18BAEB"``
      - Graph color
    * - fill_color
      - ``"1667EB.3"``
      - Fill color for linefill graph
    * - background
      - ``"000000"``
      - Widget background
    * - border_color
      - ``"215578"``
      - Widget border color
    * - border_width
      - ``2``
      - Widget background
    * - margin_x
      - ``3``
      - Margin X
    * - margin_y
      - ``3``
      - Margin Y
    * - samples
      - ``100``
      - Count of graph samples.
    * - frequency
      - ``1``
      - Update frequency in seconds
    * - type
      - ``"linefill"``
      - 'box', 'line', 'linefill'
    * - line_width
      - ``3``
      - Line width
    * - start_pos
      - ``"bottom"``
      - Drawer starting position ('bottom'/'top')


NetGraph
~~~~~~~~

Display a network usage graph.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - graph_color
      - ``"18BAEB"``
      - Graph color
    * - fill_color
      - ``"1667EB.3"``
      - Fill color for linefill graph
    * - background
      - ``"000000"``
      - Widget background
    * - border_color
      - ``"215578"``
      - Widget border color
    * - border_width
      - ``2``
      - Widget background
    * - margin_x
      - ``3``
      - Margin X
    * - margin_y
      - ``3``
      - Margin Y
    * - samples
      - ``100``
      - Count of graph samples.
    * - frequency
      - ``1``
      - Update frequency in seconds
    * - type
      - ``"linefill"``
      - 'box', 'line', 'linefill'
    * - line_width
      - ``3``
      - Line width
    * - interface
      - ``"auto"``
      - Interface to display info for ('auto' for detection, or e.g. eth0).
    * - bandwidth_type
      - ``"down"``
      - down(load)/up(load)
    * - start_pos
      - ``"bottom"``
      - Drawer starting position ('bottom'/'top')


SwapGraph
~~~~~~~~~

Display a swap info graph.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - graph_color
      - ``"18BAEB"``
      - Graph color
    * - fill_color
      - ``"1667EB.3"``
      - Fill color for linefill graph
    * - background
      - ``"000000"``
      - Widget background
    * - border_color
      - ``"215578"``
      - Widget border color
    * - border_width
      - ``2``
      - Widget background
    * - margin_x
      - ``3``
      - Margin X
    * - margin_y
      - ``3``
      - Margin Y
    * - samples
      - ``100``
      - Count of graph samples.
    * - frequency
      - ``1``
      - Update frequency in seconds
    * - type
      - ``"linefill"``
      - 'box', 'line', 'linefill'
    * - line_width
      - ``3``
      - Line width
    * - start_pos
      - ``"bottom"``
      - Drawer starting position ('bottom'/'top')


Misc
----


Clipboard
~~~~~~~~~

Display current clipboard contents.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - selection
      - ``"CLIPBOARD"``
      - the selection to display (CLIPBOARD or PRIMARY)
    * - max_width
      - ``10``
      - maximum number of characters to display. ``None`` for all, useful when width is ``bar.STRETCH``
    * - timeout
      - ``10``
      - Default timeout (seconds) for display text, None to keep forever.
    * - blacklist
      - ``["keepassx"]``
      - list with blacklisted wm_class, sadly not every clipboard window sets them, keepassx does.
        Clipboard contents from blacklisted wm_classes will be replaced by the value of ``blacklist_text``.
    * - blacklist_text
      - ``"***********"``
      - text to display when the wm_class is blacklisted.


Countdown
~~~~~~~~~

A simple countdown timer text widget.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - format
      - ``"{D}d {H}h {M}m {S}s"``
      - Format of the displayed text. Available variables:  {D} == days, {H} == hours, {M} == minutes, {S} seconds.
    * - update_interval
      - ``1.``
      - Update interval in seconds for the clock
    * - date
      - ``datetime.now()``
      - The datetime for the endo of the countdown


DF
~~

Disk Free Widget
By default the widget only displays if the space is less than warn_space

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - partition
      - ``"/"``
      - the partition to check space
    * - warn_color
      - ``"ff0000"``
      - Warning color
    * - warn_space
      - ``2``
      - Warning space in scale defined by the ``measure`` option.
    * - visible_on_warn
      - ``True``
      - Only display if warning. False == always display
    * _ measure
      - ``"G"``
      - Measurement in G == Gigabytes, M == Megabytes or B == Bytes
    * - format
      - ``"{p} ({uf}{m})"``
      - String format p: partition, s: size, f: free space, uf: user free space, m: measure
    * - update_interval
      - ``60``
      - The update inteval in seconds

Image
~~~~~

Display a PNG image on the bar.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - scale
      - ``True``
      - Enable/Disable image scaling
    * - filename
      - ``None``
      - PNG Image filename. Can contain '~'. Must be set.


Notify
~~~~~~

An notify widget

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - widget font
    * - fontsize
      - ``None``
      - widget pixel size. Calculated if None.
    * - padding
      - ``None``
      - widget padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground normal priority colour
    * - foreground_urgent
      - ``"ff0000"``
      - Foreground urgent priority colour
    * - foreground_low
      - ``"dddddd"``
      - Foreground low priority colour


Prompt
~~~~~~

A widget that prompts for user input. Input should be started using the
.startInput method on this class.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Font pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - cursorblink
      - ``0.5``
      - Cursor blink rate. 0 to disable.


Sep
~~~

A visible widget separator.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - padding
      - ``2``
      - Padding on either side of separator.
    * - linewidth
      - ``1``
      - Width of separator line.
    * - foreground
      - ``"888888"``
      - Separator line colour.
    * - background
      - ``"000000"``
      - Background colour.
    * - height_percent
      - ``80``
      - Height as a percentage of bar height (0-100).


Spacer
~~~~~~

Just an empty space on the bar. Often used with width equal to
bar.STRETCH to push bar widgets to the right edge of the screen.


System
------


Battery
~~~~~~~

A simple but flexible text-based battery widget.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - low_foreground
      - ``"FF0000"``
      - font color when battery is low
    * - format
      - ``"{char} {percent:2.0%} {hour:d}:{min:02d}"``
      - Display format
    * - charge_char
      - ``"^"``
      - Character to indicate the battery is charging
    * - discharge_char
      - ``"V"``
      - Character to indicate the battery is discharging
    * - font
      - ``"Arial"``
      - Text font
    * - fontsize
      - ``None``
      - Font pixel size. Calculated if None.
    * - padding
      - ``3``
      - Padding left and right. Calculated if None.
    * - background
      - ``None``
      - Background colour.
    * - foreground
      - ``"#ffffff"``
      - Foreground colour.
    * - battery_name
      - ``"BAT0"``
      - ACPI name of a battery, usually BAT0
    * - status_file
      - ``"status"``
      - Name of status file in /sys/class/power_supply/battery_name
    * - energy_now_file
      - ``"energy_now"``
      - Name of file with the current energy in /sys/class/power_supply/battery_name
    * - energy_full_file
      - ``"energy_full"``
      - Name of file with the maximum energy in /sys/class/power_supply/battery_name
    * - power_now_file
      - ``"power_now"``
      - Name of file with the current power draw in /sys/class/power_supply/battery_name
    * - update_delay
      - ``1``
      - The delay in seconds between updates


BatteryIcon
~~~~~~~~~~~

Battery life indicator widget

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - theme_path
      - ``"libqtile/resources/battery-icons"``
      - Path of the icons
    * - custom_icons
      - ``{}``
      - dict containing key->filename icon map
    * - font
      - ``"Arial"``
      - Text font
    * - fontsize
      - ``None``
      - Font pixel size. Calculated if None.
    * - padding
      - ``3``
      - Padding left and right. Calculated if None.
    * - background
      - ``None``
      - Background colour.
    * - foreground
      - ``"#ffffff"``
      - Foreground colour.
    * - battery_name
      - ``"BAT0"``
      - ACPI name of a battery, usually BAT0
    * - status_file
      - ``"status"``
      - Name of status file in /sys/class/power_supply/battery_name
    * - energy_now_file
      - ``"energy_now"``
      - Name of file with the current energy in /sys/class/power_supply/battery_name
    * - energy_full_file
      - ``"energy_full"``
      - Name of file with the maximum energy in /sys/class/power_supply/battery_name
    * - power_now_file
      - ``"power_now"``
      - Name of file with the current power draw in /sys/class/power_supply/battery_name
    * - update_delay
      - ``1``
      - The delay in seconds between updates


Clock
~~~~~

.. image:: /_static/widgets/clock.png

A simple but flexible text-based clock.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Clock font
    * - fontsize
      - ``None``
      - Clock pixel size. Calculated if None.
    * - padding
      - ``None``
      - Clock padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour

KeyboardLayout
~~~~~~~~~~~~~~

Widget for changing and displaying the current keyboard layout.
        It requires setxkbmap to be available in the sytem.

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``None``
      - Pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding. Calculated if None.
    * - background
      - ``"000000"``
      - Background colour
    * - foreground
      - ``"ffffff"``
      - Foreground colour
    * - update_interval
      - ``1``
      - Update time in seconds
    * - configured_keyboards
      - us
      - A list of predefined keyboard layouts represented as strings. For example: ['us', 'us colemak', 'es', 'fr'].


LaunchBar
~~~~~~~~~

A widget that display icons to launch the associated command


.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - padding
      - ``2``
      - Padding in pixels between icons
    * - default_icon
      - ``"/usr/share/icons/oxygen/256x256/mimetypes/application-x-executable.png"``
      - Default icon to use if application icon wasn't found'
    * - progs
      -
      - A list of tuples (software_name, command_to_execute, comment)
        for example:
        ``[('thunderbird', 'thunderbird -safe-mode', 'launch thunderbird in safe mode'),
        ('logout', 'qsh:self.qtile.cmd_shutdown()', 'logout from qtile'),]``


Systray
~~~~~~~

A widget that manage system tray

.. image:: /_static/widgets/systray.png

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - icon_size
      - ``20``
      - Icon width
    * - padding
      - ``5``
      - Padding between icons
    * - background
      - ``None``
      - Background colour


Volume
~~~~~~

Widget that display and change volume
if theme_path is set it draw widget as
icons

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - cardid
      - ``0``
      - Card Id
    * - channel
      - ``'Master"``
      - Channel
    * - font
      - ``"Arial"``
      - Text font
    * - fontsize
      - ``None``
      - Font pixel size. Calculated if None.
    * - padding
      - ``3``
      - Padding left and right. Calculated if None.
    * - background
      - ``None``
      - Background colour.
    * - foreground
      - ``"#ffffff"``
      - Foreground colour.
    * - theme_path
      - ``None``
      - Path of the icons
    * - update_interval
      - ``0.2``
      - Update time in seconds.


Window Management
-----------------

CurrentLayout
~~~~~~~~~~~~~

Display the name of the current layout of the current group of the screen, the bar containing the widget, is on.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Text font
    * - fontsize
      - ``None``
      - Font pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding left and right. Calculated if None.
    * - background
      - ``None``
      - Background colour.
    * - foreground
      - ``"#ffffff"``
      - Foreground colour.
    * - fontshadow
      - ``None``
      - font shadow color, default is None (no shadow)

GroupBox
~~~~~~~~

A widget that graphically displays the current group.

.. image:: /_static/widgets/groupbox.png

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - active
      - ``"ffffff"``
      - Active group font colour
    * - inactive
      - ``"404040"``
      - Inactive group font colour
    * - urgent_text
      - ``"FF0000"``
      - Urgent group font color
    * - margin_y
      - ``3``
      - Y margin outside the box
    * - margin_x
      - ``3``
      - X margin outside the box
    * - borderwidth
      - ``3``
      - Current group border width
    * - font
      - ``"Arial"``
      - Font face
    * - fontsize
      - ``None``
      - Font pixel size - calculated if None
    * - background
      - ``"000000"``
      - Widget background
    * - highlight_method
      - ``"border"``
      - Method of highlighting (one of 'border' or 'block') Uses \*_border color settings
    * - rounded
      - ``True``
      - To round or not to round borders
    * - this_current_screen_border
      - ``"215578"``
      - Border colour for group on this screen when focused.
    * - this_screen_border
      - ``"113358"``
      - Border colour for group on this screen.
    * - other_screen_border
      - ``"404040"``
      - Border colour for group on other screen.
    * - padding
      - ``5``
      - Padding inside the box
    * - urgent_border
      - ``"FF0000"``
      - Urgent border color
    * - urgent_alert_method
      - ``"border"``
      - Method for alerting you of WM urgent hints (one of 'border' or 'text')
    * - disable_drag
      - ``False``
      - Disable dragging and dropping of group names on widget.
    * - invert_mouse_wheel
      - ``False``
      - Whether to invert mouse wheel group movement.


WindowName
~~~~~~~~~~

Displays the name of the window that currently has focus.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - font
      - ``"Arial"``
      - Font face.
    * - fontsize
      - ``None``
      - Font pixel size. Calculated if None.
    * - padding
      - ``None``
      - Padding left and right.
    * - background
      - ``"000000"``
      - Background colour.
    * - foreground
      - ``"ffffff"``
      - Foreground colour.
