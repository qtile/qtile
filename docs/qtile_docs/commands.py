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
import importlib
import inspect

from docutils.parsers.rst import Directive, directives
from qtile_docs.base import SimpleDirectiveMixin, command_nodes
from qtile_docs.templates import qtile_commands_template

from libqtile import command
from libqtile.utils import import_class


class QtileCommands(SimpleDirectiveMixin, Directive):
    """
    A custom directive that is used to display the commands exposed to
    the command graph for a given object.

    This is used to ensure the public API is up to date in our documentation.

    Any CommandObject with a command decorated with `@expose_command` will
    appear in the list of available commands.
    """

    optional_arguments = 8

    option_spec = {
        "baseclass": directives.unchanged,
        # includebase: Includes the baseclass object in the results
        "includebase": directives.flag,
        # object-node: name of the node on the command graph (e.g. widget, group etc.)
        "object-node": command_nodes,
        # object-selector-name: the object's selector is the object's name
        "object-selector-name": directives.flag,
        # object-selector-id: the object's selector is a numeric ID
        "object-selector-id": directives.flag,
        # object-selector-string: the object's selector is a custom strinh
        "object-selector-string": str,
        # no-title: don't include the object's name in the output
        # (useful when object has generic name e.g. backend Cors objects)
        "no-title": directives.flag,
        # exclude-command-object-methods: exclude methods inherited from CommandObject
        "exclude-command-object-methods": directives.flag,
    }

    def get_class_commands(self, cls, exclude_inherited=False):
        commands = []

        for attr in dir(cls):
            # Some attributes will result in an AttributeError so we can skip them
            if not hasattr(cls, attr):
                continue

            method = getattr(cls, attr)

            # If it's not a callable method then we don't need to look at it
            if not callable(method):
                continue

            # Check if method has been exposed to the command graph
            if getattr(method, "_cmd", False):
                # If we're excluding inherited commands then check for them here
                if exclude_inherited and hasattr(command.base.CommandObject, method):
                    continue

                commands.append(attr)

        return commands

    def make_interface_syntax(self, obj):
        """
        Builds strings to show the lazy and cmd-obj syntax
        used to access the commands for the given object.
        """
        lazy = "lazy"
        cmdobj = ["qtile", "cmd-obj", "-o"]

        # Get the node on the command graph
        node = self.options.get("object-node", "")

        if not node:
            # cmd-obj needs the root note to be specified
            cmdobj.append("cmd")
        else:
            lazy += f".{node}"
            cmdobj.append(node)

        # Give an example of an object selector
        if "object-selector-name" in self.options:
            name = obj.__name__.lower()
            lazy += f'["{name}"]'
            cmdobj.append(name)

        elif "object-selector-id" in self.options:
            lazy += "[ID]"
            cmdobj.append("[ID]")

        elif "object-selector-string" in self.options:
            selector = self.options["object-selector-string"]
            lazy += f'["{selector}"]'
            cmdobj.append(selector)

        # Add syntax to call the command
        lazy += ".<command>()"
        cmdobj.extend(["-f", "<command>"])

        interfaces = {"lazy": lazy, "cmdobj": " ".join(cmdobj)}

        return interfaces

    def make_rst(self):
        module = importlib.import_module(self.arguments[0])
        exclude_inherited = "exclude-command-object-methods" in self.options
        includebase = "includebase" in self.options

        no_title = "no-title" in self.options

        baseclass = self.options.get("baseclass", "libqtile.command.base.CommandObject")

        self.baseclass = import_class(*baseclass.rsplit(".", 1))

        for item in dir(module):
            obj = import_class(self.arguments[0], item)

            if (
                not inspect.isclass(obj)
                or not issubclass(obj, self.baseclass)
                or (obj is self.baseclass and not includebase)
            ):
                continue

            commands = sorted(self.get_class_commands(obj, exclude_inherited))

            context = {
                "objectname": f"{obj.__module__}.{obj.__name__}",
                "module": obj.__module__,
                "baseclass": obj.__name__,
                "underline": "=" * len(obj.__name__),
                "commands": commands,
                "no_title": no_title,
                "interfaces": self.make_interface_syntax(obj),
            }
            rst = qtile_commands_template.render(**context)
            for line in rst.splitlines():
                yield line
