import os
from subprocess import CalledProcessError, run

from qtile_docs.collapsible import (
    CollapsibleNode,
    CollapsibleSection,
    depart_collapsible_node,
    visit_collapsible_node,
)
from qtile_docs.commands import QtileCommands
from qtile_docs.graph import QtileGraph
from qtile_docs.hooks import QtileHooks
from qtile_docs.migrations import QtileMigrations
from qtile_docs.module import QtileModule
from qtile_docs.qtile_class import QtileClass

this_dir = os.path.dirname(__file__)
base_dir = os.path.abspath(os.path.join(this_dir, ".."))


def generate_keybinding_images():
    try:
        run(["make", "-C", this_dir, "genkeyimg"], check=True)
    except CalledProcessError:
        raise Exception("Keybinding images failed to build.")


def generate_widget_screenshots():
    try:
        run(["make", "-C", this_dir, "genwidgetscreenshots"], check=True)
    except CalledProcessError:
        raise Exception("Widget screenshots failed to build.")


def setup(app):
    generate_keybinding_images()
    if os.getenv("QTILE_NO_BUILD_SCREENSHOTS", False):
        print("Skipping screenshot builds...")
    else:
        generate_widget_screenshots()

    app.add_directive("qtile_class", QtileClass)
    app.add_directive("qtile_hooks", QtileHooks)
    app.add_directive("qtile_module", QtileModule)
    app.add_directive("qtile_commands", QtileCommands)
    app.add_directive("qtile_graph", QtileGraph)
    app.add_directive("qtile_migrations", QtileMigrations)
    app.add_directive("collapsible", CollapsibleSection)
    app.add_node(CollapsibleNode, html=(visit_collapsible_node, depart_collapsible_node))
