import libcst as cst
import libcst.matchers as m

from libqtile.scripts.migrations._base import (
    Check,
    MigrationTransformer,
    _QtileMigrator,
    add_migration,
)


class WlanArgsTransformer(MigrationTransformer):
    @m.call_if_inside(m.Call(func=m.Name("Wlan")) | m.Call(func=m.Attribute(attr=m.Name("Wlan"))))
    @m.leave(m.Arg(keyword=m.Name("ethernet_message")))
    def update_wlan_args(self, original_node, updated_node) -> cst.Arg:
        """Changes 'ethernet_message' to 'ethernet_message_format'."""
        self.lint(
            original_node,
            "The 'ethernet_message' argument is deprecated and should be replaced with 'ethernet_message_format'.",
        )
        return updated_node.with_changes(keyword=cst.Name("ethernet_message_format"))


class WlanArgs(_QtileMigrator):
    ID = "UpdateWlanArgs"

    SUMMARY = "Updates ``Wlan`` argument signature."

    HELP = """
    The ``Wlan`` widget previously accepted a ``ethernet_message`` keyword argument. This has
    been deprecated and should be replaced with a keyword argument named ``ethernet_message_format``.

    For example:

    .. code:: python

        widget.Wlan(ethernet_message="eth")

    should be changed to:

    .. code::

        widget.Wlan(ethernet_message_format="eth")

    """

    AFTER_VERSION = "0.31.0"

    TESTS = [
        Check(
            """
            from libqtile import bar, widget
            from libqtile.widget import Wlan

            bar.Bar(
                [
                    Wlan(ethernet_message="eth"),
                    widget.Wlan(ethernet_message="eth"),
                ],
                20,
            )
            """,
            """
            from libqtile import bar, widget
            from libqtile.widget import Wlan

            bar.Bar(
                [
                    Wlan(ethernet_message_format="eth"),
                    widget.Wlan(ethernet_message_format="eth"),
                ],
                20,
            )
            """,
        ),
    ]

    visitor = WlanArgsTransformer


add_migration(WlanArgs)
