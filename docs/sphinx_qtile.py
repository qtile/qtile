# Copyright (c) 2015 dmpayton
# Copyright (c) 2021 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
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
    run(["make", "-C", base_dir, "run-ffibuild"])
    generate_keybinding_images()
    # screenshots will be skipped unless QTILE_BUILD_SCREENSHOTS environment variable is set
    # Variable is set for ReadTheDocs at https://readthedocs.org/dashboard/qtile/environmentvariables/
    if os.getenv("QTILE_BUILD_SCREENSHOTS", False):
        generate_widget_screenshots()
    else:
        print("Skipping screenshot builds...")

    app.add_directive("qtile_class", QtileClass)
    app.add_directive("qtile_hooks", QtileHooks)
    app.add_directive("qtile_module", QtileModule)
    app.add_directive("qtile_commands", QtileCommands)
    app.add_directive("qtile_graph", QtileGraph)
    app.add_directive("qtile_migrations", QtileMigrations)
    app.add_directive("collapsible", CollapsibleSection)
    app.add_node(CollapsibleNode, html=(visit_collapsible_node, depart_collapsible_node))
