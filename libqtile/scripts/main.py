import argparse
import logging
import sys

import typer
from typer import Option

from libqtile.scripts import check, cmd_obj, migrate, run_cmd, shell, start, top

try:
    # Python>3.7 can get the version from importlib
    from importlib.metadata import distribution  # type: ignore
    VERSION = distribution("qtile").version
except ModuleNotFoundError:
    try:
        # pkg_resources is required for 3.7
        import pkg_resources
        VERSION = pkg_resources.require("qtile")[0].version
    except (pkg_resources.DistributionNotFound, ModuleNotFoundError):
        VERSION = 'dev'

app = typer.Typer(
    help="A full-featured, pure-Python tiling window manager.",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)
app.command()(start.start)
app.command()(shell.shell)
app.command()(top.top)
app.command()(run_cmd.run_cmd)
app.command()(cmd_obj.cmd_obj)
app.command()(check.check)
app.command()(migrate.migrate)


def _print_version(do):
    if do:
        typer.echo(f"Your Qtile version is: {VERSION}")
        raise typer.Exit()


def _print_help(do):
    if do:
        typer.echo(f"HELP")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = Option(False, "--version", callback=_print_version, is_eager=True),
):
    pass


if __name__ == "__main__":
    app()
