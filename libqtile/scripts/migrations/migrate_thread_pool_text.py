from libqtile.scripts.migrations._base import (
    Check,
    RenamerTransformer,
    _QtileMigrator,
    add_migration,
)


class MigrateThreadPoolTextTransformer(RenamerTransformer):
    from_to = ("ThreadPoolText", "BackgroundPoll")


class MigrateThreadPoolText(_QtileMigrator):
    ID = "MigrateThreadPoolText"

    SUMMARY = "Replaces ``ThreadPoolText`` with ``BackgroundPoll``."

    HELP = """
    The ``ThreadPoolText`` class is deprecated and should be replaced with
    ``BackgroundPoll``.
    """

    AFTER_VERSION = "0.33.0"

    TESTS = [
        Check(
            """
            from libqtile.widget.base import ThreadPoolText

            class MyWidget(ThreadPoolText):
                pass
            """,
            """
            from libqtile.widget.base import BackgroundPoll

            class MyWidget(BackgroundPoll):
                pass
            """,
        ),
        Check(
            """
            from libqtile.widget import base

            class MyWidget(base.ThreadPoolText):
                def __init__(self, **config):
                    base.ThreadPoolText.__init__(self, "", **config)

                def poll(self):
                    return "some text"
            """,
            """
            from libqtile.widget import base

            class MyWidget(base.BackgroundPoll):
                def __init__(self, **config):
                    base.BackgroundPoll.__init__(self, "", **config)

                def poll(self):
                    return "some text"
            """,
        ),
    ]

    visitor = MigrateThreadPoolTextTransformer


add_migration(MigrateThreadPoolText)
