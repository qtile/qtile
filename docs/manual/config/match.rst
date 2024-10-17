.. _match:

================
Matching windows
================

Qtile's config provides a number of situations where the behaviour depends
on whether the relevant window matches some specified criteria.

These situations include:

  - Defining which windows should be floated by default
  - Assigning windows to specific groups
  - Assigning window to a master section of a layout

In each instance, the criteria are defined via a ``Match`` object. The properties
of the object will be compared to a :class:`~libqtile.base.Window` to determine if
its properties *match*. It can match by title, wm_class, role, wm_type,
wm_instance_class, net_wm_pid, or wid. Additionally, a function may be
passed, which takes in the :class:`~libqtile.base.Window` to be compared
against and returns a boolean.

A basic rule would therefore look something like:

.. code::  python

    Match(wm_class="mpv")

This would match against any window whose class was ``mpv``.

Where a string is provided as an argument then the value must match exactly. More
flexibility can be achieved by using regular expressions. For example:

.. code::  python

    import re

    Match(wm_class=re.compile(r"mpv"))

This would still match a window whose class was ``mpv`` but it would also match
any class starting with ``mpv`` e.g. ``mpvideo``.

.. note::

    When providing a regular expression, qtile applies the ``.match`` method.
    This matches from the start of the string so, if you want to match any substring,
    you will need to adapt the regular expression accordingly e.g.

    .. code::  python

        import re

        Match(wm_class=re.compile(r".*mpv"))

    This would match any string containing ``mpv``

Creating advanced rules
=======================

While the ``func`` parameter allows users to create more complex matches, this requires
a knowledge of qtile's internal objects. An alternative is to combine Match objects using
logical operators ``&`` (and), ``|`` (or), ``~`` (not) and ``^`` (xor).

For example, to create rule that matches all windows with a fixed aspect ratio except for
mpv windows, you would provide the following:

.. code::  python

    Match(func=lambda c: c.has_fixed_ratio()) & ~Match(wm_class="mpv")

It is also possible to use wrappers for ``Match`` objects if you do not want to use the
operators. The following wrappers are available:

  - ``MatchAll(Match(...), ...)`` equivalent to "and" test. All matches must match.
  - ``MatchAny(Match(...), ...)`` equivalent to "or" test. At least one match must match.
  - ``MatchOnlyOne(Match(...), Match(...))`` equivalent to "xor". Only one match must match.
  - ``InvertMatch(Match(...))`` equivalent to "not". Inverts the result of the match.

So, to recreate the above rule using the wrappers, you would write the following:

.. code::  python

    from libqtile.config import InvertMatch, Match, MatchAll

    MatchAll(Match(func=lambda c: c.has_fixed_ratio()), InvertMatch(Match(wm_class="mpv")))
