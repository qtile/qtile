.. _widget-creation:

======================
How to create a widget
======================

The aim of this page is to explain the main components of qtile widgets, how
they work, and how you can use them to create your own widgets.

.. note::
    This page is not meant to be an exhaustive summary of everything needed to
    make a widget.

    It is highly recommended that users wishing to create their own widget refer
    to the source documentation of existing widgets to familiarise themselves with
    the code.

    However, the detail below may prove helpful when read in conjunction with the
    source code.

What is a widget?
=================

In Qtile, a widget is a small drawing that is displayed on the user's bar. The
widget can display text, images and drawings. In addition, the widget can be
configured to update based on timers, hooks, dbus_events etc. and can also
respond to mouse events (clicks, scrolls and hover).

Widget base classes
===================

Qtile provides a number of base classes for widgets than can be used to implement
commonly required features (e.g. display text).

Your widget should inherit one of these classes. Whichever base class you inherit
for your widget, if you override either the ``__init__`` and/or ``_configure``
methods, you should make sure that your widget calls the equivalent method from
the superclass.

.. code:: python

    class MyCustomWidget(base._TextBox):

        def __init__(self, **config):
            super().__init__("", **config)
            # My widget's initialisation code here

The functions of the various base classes are explained further below.

_Widget
-------

This is the base widget class that defines the core components required for a widget.
All other base classes are based off this class.

This is like a blank canvas so you're free to do what you want but you don't have any
of the extra functionality provided by the other base classes.

The ``base._Widget`` class is therefore typically used for widgets that want to draw
graphics on the widget as opposed to displaying text.

_TextBox
--------

The ``base._TextBox`` class builds on the bare widget and adds a ``drawer.TextLayout``
which is accessible via the ``self.layout`` property. The widget will adjust its size
to fit the amount of text to be displayed.

Text can be updated via the ``self.text`` property but note that this does not trigger
a redrawing of the widget.

Parameters including ``font``, ``fontsize``, ``fontshadow``, ``padding`` and
``foreground`` (font colour) can be configured. It is recommended not to hard-code
these parameters as users may wish to have consistency across units.

InLoopPollText
--------------

The ``base.InLoopPollText`` class builds on the ``base._TextBox`` by adding a timer to
periodically refresh the displayed text.

Widgets using this class should override the ``poll`` method to include a function that
returns the required text.

.. note::
    This loop runs in the event loop so it is important that the poll method does not
    call some blocking function. If this is required, widgets should inherit the
    ``base.ThreadPoolText`` class (see below).

ThreadPoolText
--------------

The ``base.ThreadPoolText`` class is very similar to the ``base.InLoopPollText`` class.
The key difference is that the ``poll`` method is run asynchronously and triggers a
callback once the function completes. This allows widgets to get text from
long-running functions without blocking Qtile.

Mixins
======

As well as inheriting from one of the base classes above, widgets can also inherit one
or more mixins to provide some additional functionality to the widget.

PaddingMixin
------------

This provides the ``padding(_x|_y|)`` attributes which can be used to change the
appearance of the widget. And ``padding(_side|_top|)`` properties to get the appropriate
value based on bar orientation.

MarginMixin
-----------

This is essentially exactly the same as the before, but instead, it provides the
``margin(_x|_y|)`` attributes. And the bar oriented ``margin(_side|_top|)`` properties.

Configuration
=============

Now you know which class to base your widget on, you need to know how the widget
gets configured.

Defining Parameters
-------------------

Each widget will likely have a number of parameters that users can change to
customise the look and feel and/or behaviour of the widget for their own needs.

The widget should therefore provide the default values of these parameters as a
class attribute called ``defaults``. The format of this attribute is a list of
tuples.

.. code:: python

    defaults = [
        ("parameter_name",
         default_parameter_value,
         "Short text explaining what parameter does")
    ]

Users can override the default value when creating their ``config.py`` file.

.. code:: python

    MyCustomWidget(parameter_name=updated_value)

Once the widget is initialised, these parameters are available at
``self.parameter_name``.

The __init__ method
-------------------

Parameters that should not be changed by users can be defined in the ``__init__``
method.

This method is run when the widgets are initially created. This happens before
the ``qtile`` object is available.

The _configure method
---------------------

The ``_configure`` method is called by the ``bar`` object and sets the
``self.bar`` and ``self.qtile`` attributes of the widget. It also creates the
``self.drawer`` attribute which is necessary for displaying any content.

Once this method has been run, your widget should be ready to display content as
the bar will draw once it has finished its configuration.

Calls to methods required to prepare the content for your widget should therefore
be made from this method rather than ``__init__``.

Displaying output
=================

A Qtile widget is just a drawing that is displayed at a certain location the
user's bar. The widget's job is therefore to create a small drawing surface that
can be placed in the appropriate location on the bar.

The "draw" method
-----------------

The ``draw`` method is called when the widget needs to update its appearance.
This can be triggered by the widget itself (e.g. if the content has changed) or
by the bar (e.g. if the bar needs to redraw its entire contents).

This method therefore needs to contain all the relevant code to draw the various
components that make up the widget. Examples of displaying text, icons and
drawings are set out below.

It is important to note that the bar controls the placing of the widget by
assigning the ``offsetx`` value (for horizontal positioning) and ``offsety``
value (for vertical positioning). While the widget controls its ``width`` and
``height``. These four values should be use at the end of the ``draw`` method.
It is recommended to call this helper function to do it automatically:

.. code:: python

    self.draw_at_default_position()

.. note::

    If you need to trigger a redrawing of your widget, you should call
    ``self.draw()`` if the width of your widget is unchanged. Otherwise you
    need to call ``self.bar.draw()`` as this method means the bar recalculates
    the position of all widgets.

Displaying text
---------------

Text is displayed by using a ``drawer.TextLayout`` object. If all you are doing is
displaying text then it's highly recommended that you use the ``base._TextBox``
superclass as this simplifies adding and updating text.

If you wish to implement this manually then you can create a your own ``drawer.TextLayout``
by using the ``self.drawer.textlayout`` method of the widget (only available after
the `_configure` method has been run). object to include in your widget.

Some additional formatting of Text can be displayed using pango markup and ensuring
the ``markup`` parameter is set to ``True``.

.. code:: python

    self.textlayout = self.drawer.textlayout(
                         "Text",
                         "fffff",       # Font colour
                         "sans",        # Font family
                         12,            # Font size
                         None,          # Font shadow
                         markup=False,  # Pango markup (False by default)
                         wrap=True      # Wrap long lines (True by default)
                         )

Displaying icons and images
---------------------------

Qtile provides a helper library to convert images to a ``surface`` that can be
drawn by the widget. If the images are static then you should only load them
once when the widget is configured. Given the small size of the bar, this is
most commonly used to draw icons but the same method applies to other images.

.. code:: python

    from libqtile import images

    def setup_images(self):

        self.surfaces = {}

        # File names to load (will become keys to the `surfaces` dictionary)
        names = (
            "audio-volume-muted",
            "audio-volume-low",
            "audio-volume-medium",
            "audio-volume-high"
        )

        d_images = images.Loader(self.imagefolder)(*names)  # images.Loader can take more than one folder as an argument

        new_height = self.bar.size - 2
        for name, img in d_images.items():
            img.resize(height=new_height)   # Resize images to fit widget
            self.surfaces[name] = img.pattern  # Images added to the `surfaces` dictionary

Drawing the image is then just a matter of painting it to the relevant surface:

.. code:: python

    def draw(self):
        self.drawer.ctx.set_source(self.surfaces[img_name])  # Use correct key here for your image
        self.drawer.ctx.paint()
        self.draw_at_default_position()

Drawing shapes
--------------

It is possible to draw shapes directly to the widget. The ``Drawer`` class
(available in your widget after configuration as ``self.drawer``) provides some
basic functions ``rounded_rectangle``, ``rounded_fillrect``, ``rectangle`` and
``fillrect``.

In addition, you can access the `Cairo`_ context drawing functions via ``self.drawer.ctx``.

.. _Cairo: https://pycairo.readthedocs.io/en/latest/reference/context.html

For example, the following code can draw a wifi icon showing signal strength:

.. code:: python

    import math

    ...

    def to_rads(self, degrees):
        return degrees * math.pi / 180.0

    def draw_wifi(self, percentage):

        WIFI_HEIGHT = 12
        WIFI_ARC_DEGREES = 90

        y_margin = (self.bar.size - WIFI_HEIGHT) / 2
        half_arc = WIFI_ARC_DEGREES / 2

        # Draw grey background
        self.drawer.ctx.new_sub_path()
        self.drawer.ctx.move_to(WIFI_HEIGHT, y_margin + WIFI_HEIGHT)
        self.drawer.ctx.arc(WIFI_HEIGHT,
                            y_margin + WIFI_HEIGHT,
                            WIFI_HEIGHT,
                            self.to_rads(270 - half_arc),
                            self.to_rads(270 + half_arc))
        self.drawer.set_source_rgb("666666")
        self.drawer.ctx.fill()

        # Draw white section to represent signal strength
        self.drawer.ctx.new_sub_path()
        self.drawer.ctx.move_to(WIFI_HEIGHT, y_margin + WIFI_HEIGHT)
        self.drawer.ctx.arc(WIFI_HEIGHT
                            y_margin + WIFI_HEIGHT,
                            WIFI_HEIGHT * percentage,
                            self.to_rads(270 - half_arc),
                            self.to_rads(270 + half_arc))
        self.drawer.set_source_rgb("ffffff")
        self.drawer.ctx.fill()

This creates something looking like this: |wifi_image|.

.. |wifi_image| image:: ../../_static/widgets/widget_tutorial_wifi.png

Background
----------

At the start of the ``draw`` method, the widget should clear the drawer by drawing the
background. Usually this is done by including the following line at the start of the method:

.. code:: python

    self.drawer.clear(self.background or self.bar.background)

The background can be a single colour or a list of colours which will result in a linear gradient
from top to bottom.

Vertical Orientation
--------------------

If you plan to support vertical orientation in your widget, after calling
``self.drawer.clear`` and ``self.drawer.ctx.save`` place this function
in the ``draw`` method:

.. code:: python

    self.rotate_drawer()

Updating the widget
===================

Widgets will usually need to update their content periodically. There are numerous ways
that this can be done. Some of the most common ones are summarised below.

Timers
------

A non-blocking timer can be called by using the ``self.timeout_add`` method.

.. code:: python

    self.timeout_add(delay_in_seconds, method_to_call, (method_args))

.. note::

    Consider using the ``ThreadPoolText`` superclass where you are calling a function
    repeatedly and displaying its output as text.

Hooks
-----

Qtile has a number of hooks built in which are triggered on certain events.

The ``WindowCount`` widget is a good example of using hooks to trigger updates. It
includes the following method which is run when the widget is configured:

.. code:: python

    from libqtile import hook

    ...

    def _setup_hooks(self):
        hook.subscribe.client_killed(self._win_killed)
        hook.subscribe.client_managed(self._wincount)
        hook.subscribe.current_screen_change(self._wincount)
        hook.subscribe.setgroup(self._wincount)

Read the :ref:`ref-hooks` page for details of which hooks are available and which arguments
are passed to the callback function.

Using dbus
----------

Qtile uses ``dbus-fast`` for interacting with dbus.

If you just want to listen for signals then Qtile provides a helper method called
``add_signal_receiver`` which can subscribe to a signal and trigger a callback
whenever that signal is broadcast.

.. note::
    Qtile uses the ``asyncio`` based functions of ``dbus-fast`` so your widget
    must make sure, where necessary, calls to dbus are made via coroutines.

    There is a ``_config_async`` coroutine in the base widget class which can
    be overridden to provide an entry point for asyncio calls in your widget.

For example, the Mpris2 widget uses the following code:

.. code:: python

    from libqtile.utils import add_signal_receiver

    ...

    async def _config_async(self):
        subscribe = await add_signal_receiver(
                        self.message,  # Callback function
                        session_bus=True,
                        signal_name="PropertiesChanged",
                        bus_name=self.objname,
                        path="/org/mpris/MediaPlayer2",
                        dbus_interface="org.freedesktop.DBus.Properties")

``dbus-fast`` can also be used to query properties, call methods etc. on dbus
interfaces. Refer to the `dbus-fast documentation <https://python-dbus-fast.readthedocs.io/en/latest/>`_
for more information on how to use the module.

.. _mouse-events:

Mouse events
============

By default, widgets handle button presses and will call any function that is bound to the button in the
``mouse_callbacks`` dictionary. The dictionary keys are as follows:

 - ``Button1``: Left click
 - ``Button2``: Middle click
 - ``Button3``: Right click
 - ``Button4``: Scroll up
 - ``Button5``: Scroll down
 - ``Button6``: Scroll left
 - ``Button7``: Scroll right

You can then define your button bindings in your widget (e.g. in ``__init__``):

.. code:: python

    class MyWidget(widget.TextBox)

        def __init__(self, *args, **config):
            widget.TextBox.__init__(self, *args, **kwargs)
            self.add_callbacks(
                {
                    "Button1": self.left_click_method,
                    "Button3": self.right_click_method
                }
            )

.. note::

    As well as functions, you can also bind ``LazyCall`` objects to button presses.
    For example:

    .. code:: python

        self.add_callbacks(
            {
                "Button1": lazy.spawn("xterm"),
            }
        )

In addition to button presses, you can also respond to mouse enter and leave events.
For example, to make a clock show a longer date when you put your mouse over it, you
can do the following:

.. code:: python

    class MouseOverClock(widget.Clock):
        defaults = [
            (
                "long_format",
                "%A %d %B %Y | %H:%M",
                "Format to show when mouse is over widget."
            )
        ]

        def __init__(self, **config):
            widget.Clock.__init__(self, **config)
            self.add_defaults(MouseOverClock.defaults)
            self.short_format = self.format

        def mouse_enter(self, *args, **kwargs):
            self.format = self.long_format
            self.bar.draw()

        def mouse_leave(self, *args, **kwargs):
            self.format = self.short_format
            self.bar.draw()

Exposing commands to the IPC interface
======================================

If you want to control your widget via ``lazy`` or scripting commands (such as ``qtile cmd-obj``), you
will need to expose the relevant methods in your widget. Exposing commands is done by adding the
``@expose_command()`` decorator to your method. For example:

.. code:: python

    from libqtile.command.base import expose_command
    from libqtile.widget import TextBox


    class ExposedWidget(TextBox):

        @expose_command()
        def uppercase(self):
            self.update(self.text.upper())

Text in the ``ExposedWidget`` can now be made into upper case by calling ``lazy.widget["exposedwidget"].uppercase()``
or ``qtile cmd-onj -o widget exposedwidget -f uppercase``.

If you want to expose a method under multiple names, you can pass these additional names to the decorator. For
example, decorating a method with:

.. code:: python

    @expose_command(["extra", "additional"])
    def mymethod(self):
        ...

will make make the method visible under ``mymethod``, ``extra`` and ``additional``.

Debugging
=========

You can use the ``logger`` object to record messages in the Qtile log file to help debug your
development.

.. code:: python

    from libqtile.log_utils import logger

    ...

    logger.debug("Callback function triggered")

.. note::

    The default log level for the Qtile log is ``INFO`` so you may either want to
    change this when debugging or use ``logger.info`` instead.

    Debugging messages should be removed from your code before submitting pull
    requests.

Submitting the widget to the official repo
==========================================

The following sections are only relevant for users who wish for their widgets to
be submitted as a PR for inclusion in the main Qtile repo.

Including the widget in libqtile.widget
---------------------------------------

You should include your widget in the ``widgets`` dict in ``libqtile.widget.__init__.py``.
The relevant format is ``{"ClassName": "modulename"}``.

This has a number of benefits:

- Lazy imports
- Graceful handling of import errors (useful where widget relies on third party modules)
- Inclusion in basic unit testing (see below)

Testing
-------

Any new widgets should include an accompanying unit test.

Basic initialisation and configurations (using defaults) will automatically be tested by
``test/widgets/test_widget_init_configure.py`` if the widget has been included in
``libqtile.widget.__init__.py`` (see above).

However, where possible, it is strongly encouraged that widgets include additional unit
tests that test specific functionality of the widget (e.g. reaction to hooks).

See :ref:`unit-testing` for more.

Documentation
-------------

It is really important that we maintain good documentation for Qtile. Any new widgets must
therefore include sufficient documentation in order for users to understand how to
use/configure the widget.

The majority of the documentation is generated automatically from your module. The widget's
docstring will be used as the description of the widget. Any parameters defined in the
widget's ``defaults`` attribute will also be displayed. It is essential that there is a
clear explanation of each new parameter defined by the widget.

Screenshots
~~~~~~~~~~~

While not essential, it is strongly recommended that the documentation includes one or more
screenshots.

Screenshots can be generated automatically with a minimal amount of coding by using the fixtures
created by Qtile's test suite.

A screenshot file must satisfy the following criteria:

 - Be named ``ss_[widgetname].py``
 - Any function that takes a screenshot must be prefixed with ``ss_``
 - Define a pytest fixture named ``widget``

An example screenshot file is below:

.. code:: python

    import pytest

    from libqtile.widget import wttr
    from test.widgets.docs_screenshots.conftest import vertical_bar, widget_config

    RESPONSE = "London: +17°C"


    @pytest.fixture
    def widget(monkeypatch):
        def result(self):
            return RESPONSE

        monkeypatch.setattr("libqtile.widget.wttr.Wttr.fetch", result)
        yield wttr.Wttr


    @widget_config([{"location": {"London": "Home"}}])
    def ss_wttr(screenshot_manager):
        screenshot_manager.take_screenshot()

    @vertical_bar
    def ss_wttr_vertical(screenshot_manager):
        screenshot_manager.take_screenshot()

The ``widget`` fixture returns the widget class (not an instance of the widget). Any monkeypatching
of the widget should be included in this fixture.

The screenshot function (here, called ``ss_wttr``) must take an argument called ``screenshot_manager``.
The function can also be parameterized, in which case, each dict object will be used
to configure the widget for the screenshot (and the configuration will be displayed in the docs). If
you want to include parameterizations but also want to show the default configuration, you should include
an empty dict (``{}``) as the first object in the list.

Taking a screenshot is then as simple as calling ``screenshot_manager.take_screenshot()``. The method
can be called multiple times in the same function.

Screenshots can also be taken in a vertical bar orientation by using the ``@vertical_bar`` decorator as shown in
the above example.

``screenshot_manager.take_screenshot()`` only takes a picture of the widget. If you need to take a screenshot
of the bar then you need a few extra steps:

.. code:: python

    def ss_bar_screenshot(screenshot_manager):
        # Generate a filename for the screenshot
        target = screenshot_manager.target()

        # Get the bar object
        bar = screenshot_manager.c.bar["top"]

        # Take a screenshot. Will take screenshot of whole bar unless
        # a `width` parameter is set.
        bar.take_screenshot(target, width=width)
