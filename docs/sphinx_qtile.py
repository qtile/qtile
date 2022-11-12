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
import json
import os
import pprint
from pathlib import Path
from subprocess import CalledProcessError, run
from unittest.mock import MagicMock

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import ViewList
from jinja2 import Template
from sphinx.util.nodes import nested_parse_with_titles

from libqtile import command, configurable, widget
from libqtile.utils import import_class

qtile_module_template = Template('''
.. qtile_class:: {{ module }}.{{ class_name }}
    {% if no_config %}:no-config:{% endif %}
    {% if no_commands %}:no-commands:{% endif %}
''')

qtile_class_template = Template('''
{{ class_name }}
{{ class_underline }}

.. autoclass:: {{ module }}.{{ class_name }}{% for arg in extra_arguments %}
    {{ arg }}{% endfor %}
    {% if is_widget %}
    .. compound::

        Supported bar orientations: {{ obj.orientations }}

        {% if supported_backends %}
        Only available on the following backends: {{ ", ".join(obj.supported_backends) }}
        {% endif %}
    {% endif %}
    {% if is_widget and screen_shots %}
    .. raw:: html

        <table class="docutils">
        <tr>
        <td width="50%"><b>example</b></td>
        <td width="50%"><b>config</td>
        </tr>
    {% for sshot, conf in screen_shots.items() %}
        <tr>
        <td><img src="{{ sshot }}" /></td>
        {% if conf %}
        <td><code class="docutils literal notranslate">{{ conf }}</code></td>
        {% else %}
        <td><i>default</i></td>
        {% endif %}
        </tr>
    {% endfor %}
        </table>

    {% endif %}
    {% if configurable %}
    .. list-table::
        :widths: 20 20 60
        :header-rows: 1

        * - key
          - default
          - description
        {% for key, default, description in defaults %}
        * - ``{{ key }}``
          - ``{{ default }}``
          - {{ description[1:-1] }}
        {% endfor %}
    {% endif %}
    {% if commandable %}
    {% for cmd in commands %}
    .. automethod:: {{ module }}.{{ class_name }}.{{ cmd }}
    {% endfor %}
    {% endif %}
''')

qtile_hooks_template = Template('''
.. automethod:: libqtile.hook.subscribe.{{ method }}
''')


class SimpleDirectiveMixin:
    has_content = True
    required_arguments = 1

    def make_rst(self):
        raise NotImplementedError

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, '<{0}>'.format(self.__class__.__name__))
        nested_parse_with_titles(self.state, result, node)
        return node.children


def sphinx_escape(s):
    return pprint.pformat(s, compact=False, width=10000)


class QtileClass(SimpleDirectiveMixin, Directive):
    optional_arguments = 2

    def make_rst(self):
        module, class_name = self.arguments[0].rsplit('.', 1)
        arguments = self.arguments[1:]
        obj = import_class(module, class_name)
        is_configurable = ':no-config:' not in arguments
        is_commandable = ':no-commands:' not in arguments
        is_widget = issubclass(obj, widget.base._Widget)
        arguments = [i for i in arguments if i not in (':no-config:', ':no-commands:')]

        # build up a dict of defaults using reverse MRO
        defaults = {}
        for klass in reversed(obj.mro()):
            if not issubclass(klass, configurable.Configurable):
                continue
            if not hasattr(klass, "defaults"):
                continue
            klass_defaults = getattr(klass, "defaults")
            defaults.update({
                d[0]: d[1:] for d in klass_defaults
            })
        # turn the dict into a list of ("value", "default", "description") tuples
        defaults = [
            (k, sphinx_escape(v[0]), sphinx_escape(v[1])) for k, v in sorted(defaults.items())
        ]
        if len(defaults) == 0:
            is_configurable = False

        is_widget = issubclass(obj, widget.base._Widget)

        if is_widget:
            index = Path(__file__).parent / "_static" / "screenshots" / "widgets" / "shots.json"
            try:
                with open(index, "r") as f:
                    shots = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                shots = {}

            widget_shots = shots.get(class_name.lower(), dict())
        else:
            widget_shots = {}

        widget_shots = {f"../../widgets/{class_name.lower()}/{k}.png": v for k, v in widget_shots.items()}

        context = {
            'module': module,
            'class_name': class_name,
            'class_underline': "=" * len(class_name),
            'obj': obj,
            'defaults': defaults,
            'configurable': is_configurable and issubclass(obj, configurable.Configurable),
            'commandable': is_commandable and issubclass(obj, command.base.CommandObject),
            'is_widget': is_widget,
            'extra_arguments': arguments,
            'screen_shots': widget_shots,
            'supported_backends': is_widget and obj.supported_backends
        }
        if context['commandable']:
            context['commands'] = [
                # Command methods have the "_cmd" attribute so we check for this
                # However, some modules are Mocked so we need to exclude them
                attr.__name__ for _, attr in inspect.getmembers(obj)
                if hasattr(attr, "_cmd") and not isinstance(attr, MagicMock)
            ]

        rst = qtile_class_template.render(**context)
        for line in rst.splitlines():
            yield line


class QtileHooks(SimpleDirectiveMixin, Directive):
    def make_rst(self):
        module, class_name = self.arguments[0].rsplit('.', 1)
        obj = import_class(module, class_name)
        for method in sorted(obj.hooks):
            rst = qtile_hooks_template.render(method=method)
            for line in rst.splitlines():
                yield line


class QtileModule(SimpleDirectiveMixin, Directive):
    # :baseclass: <base class path>
    # :no-commands:
    # :no-config:
    optional_arguments = 4

    def make_rst(self):
        module = importlib.import_module(self.arguments[0])

        BaseClass = None
        if ':baseclass:' in self.arguments:
            BaseClass = import_class(*self.arguments[
                self.arguments.index(':baseclass:') + 1].rsplit('.', 1))

        for item in dir(module):
            obj = import_class(self.arguments[0], item)
            if not inspect.isclass(obj) or (BaseClass and
                not issubclass(obj, BaseClass)):
                continue

            context = {
                'module': self.arguments[0],
                'class_name': item,
                'no_config': ':no-config:' in self.arguments,
                'no_commands': ':no-commands:' in self.arguments,
            }
            rst = qtile_module_template.render(**context)
            for line in rst.splitlines():
                if not line.strip():
                    continue
                yield line


def generate_keybinding_images():
    this_dir = os.path.dirname(__file__)
    base_dir = os.path.abspath(os.path.join(this_dir, ".."))
    run(['make', '-C', base_dir, 'run-ffibuild'])
    run(['make', '-C', this_dir, 'genkeyimg'])


def generate_widget_screenshots():
    this_dir = os.path.dirname(__file__)
    try:
        run(['make', '-C', this_dir, 'genwidgetscreenshots'], check=True)
    except CalledProcessError:
        raise Exception("Widget screenshots failed to build.")


def setup(app):
    generate_keybinding_images()
    # screenshots will be skipped unless QTILE_BUILD_SCREENSHOTS environment variable is set
    # Variable is set for ReadTheDocs at https://readthedocs.org/dashboard/qtile/environmentvariables/
    if os.getenv("QTILE_BUILD_SCREENSHOTS", False):
        generate_widget_screenshots()
    else:
        print("Skipping screenshot builds...")
    app.add_directive('qtile_class', QtileClass)
    app.add_directive('qtile_hooks', QtileHooks)
    app.add_directive('qtile_module', QtileModule)
