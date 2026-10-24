from libqtile.scripts.migrations._base import (
    Check,
    RenamerTransformer,
    _QtileMigrator,
    add_migration,
)


class RenameDragPollingRateTransformer(RenamerTransformer):
    from_to = ("x11_drag_polling_rate", "drag_polling_rate")


class RenameDragPollingRate(_QtileMigrator):
    ID = "RenameDragPollingRate"

    SUMMARY = "Renames ``x11_drag_polling_rate`` to ``drag_polling_rate``."

    HELP = """
    The ``x11_drag_polling_rate`` screen option has been renamed to
    ``drag_polling_rate`` because it now applies to both the X11 and
    Wayland backends.

    For example:

    .. code:: python

        Screen(x11_drag_polling_rate=60)

    should be changed to:

    .. code:: python

        Screen(drag_polling_rate=60)
    """

    AFTER_VERSION = "0.37.1"

    TESTS = [
        Check(
            """
            from libqtile.config import Screen

            screens = [Screen(x11_drag_polling_rate=60)]
            """,
            """
            from libqtile.config import Screen

            screens = [Screen(drag_polling_rate=60)]
            """,
        ),
    ]

    visitor = RenameDragPollingRateTransformer


add_migration(RenameDragPollingRate)
