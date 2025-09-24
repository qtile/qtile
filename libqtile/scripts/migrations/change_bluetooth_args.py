import libcst as cst
import libcst.matchers as m

from libqtile.scripts.migrations._base import (
    Check,
    MigrationTransformer,
    _QtileMigrator,
    add_migration,
)


class BluetoothArgsTransformer(MigrationTransformer):
    @m.call_if_inside(
        m.Call(func=m.Name("Bluetooth")) | m.Call(func=m.Attribute(attr=m.Name("Bluetooth")))
    )
    @m.leave(m.Arg(keyword=m.Name("hci")))
    def update_bluetooth_args(self, original_node, updated_node) -> cst.Arg:
        """Changes positional  argumentto 'widgets' kwargs."""
        self.lint(
            original_node,
            "The 'hci' argument is deprecated and should be replaced with 'device'.",
        )
        return updated_node.with_changes(keyword=cst.Name("device"))


class BluetoothArgs(_QtileMigrator):
    ID = "UpdateBluetoothArgs"

    SUMMARY = "Updates ``Bluetooth`` argument signature."

    HELP = """
    The ``Bluetooth`` widget previously accepted a ``hci`` keyword argument. This has
    been deprecated following a major overhaul of the widget and should be replaced with
    a keyword argument named ``device``.

    For example:

    .. code:: python

        widget.Bluetooth(hci="/dev_XX_XX_XX_XX_XX_XX")

    should be changed to:

    .. code::

        widget.Bluetooth(device="/dev_XX_XX_XX_XX_XX_XX")

    """

    AFTER_VERSION = "0.23.0"

    TESTS = [
        Check(
            """
            from libqtile import bar, widget
            from libqtile.widget import Bluetooth

            bar.Bar(
                [
                    Bluetooth(hci="/dev_XX_XX_XX_XX_XX_XX"),
                    widget.Bluetooth(hci="/dev_XX_XX_XX_XX_XX_XX"),
                ],
                20,
            )
            """,
            """
            from libqtile import bar, widget
            from libqtile.widget import Bluetooth

            bar.Bar(
                [
                    Bluetooth(device="/dev_XX_XX_XX_XX_XX_XX"),
                    widget.Bluetooth(device="/dev_XX_XX_XX_XX_XX_XX"),
                ],
                20,
            )
            """,
        ),
    ]

    visitor = BluetoothArgsTransformer


add_migration(BluetoothArgs)
