# Copyright (c) 2015 dmpayton
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
from docutils import nodes
from docutils.statemachine import ViewList
from jinja2 import Template
from libqtile import command, configurable, widget
from six import class_types
from six.moves import builtins
from sphinx.util.compat import Directive
from sphinx.util.nodes import nested_parse_with_titles


qtile_module_template = Template('''
.. qtile_class:: {{ module }}.{{ class_name }}
    {% if no_config %}:no-config:{% endif %}
    {% if no_commands %}:no-commands:{% endif %}
''')

qtile_class_template = Template('''
.. autoclass:: {{ module }}.{{ class_name }}
    :members: __init__
    {% if is_widget %}
    Supported bar orientations: {{ obj.orientations }}
    {% endif %}
    {% if configurable %}
    .. list-table::
        :widths: 20 20 60
        :header-rows: 1

        * - key
          - default
          - description
        {% for key, default, description in obj.defaults %}
        * - ``{{ key }}``
          - ``{{ default|pprint }}``
          - {{ description }}
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


# Adapted from sphinxcontrib-httpdomain
def import_object(module_name, expr):
    mod = __import__(module_name)
    mod = reduce(getattr, module_name.split('.')[1:], mod)
    globals = builtins
    if not isinstance(globals, dict):
        globals = globals.__dict__
    return eval(expr, globals, mod.__dict__)


class SimpleDirectiveMixin(object):
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


class QtileClass(SimpleDirectiveMixin, Directive):
    optional_arguments = 2

    def make_rst(self):
        module, class_name = self.arguments[0].rsplit('.', 1)
        obj = import_object(module, class_name)
        context = {
            'module': module,
            'class_name': class_name,
            'obj': obj,
            'configurable': ':no-config:' not in self.arguments and
                issubclass(obj, configurable.Configurable),
            'commandable': ':no-commands:' not in self.arguments and
                issubclass(obj, command.CommandObject),
            'is_widget': issubclass(obj, widget.base._Widget),
        }
        if context['commandable']:
            context['commands'] = [attr for attr in dir(obj)
                if attr.startswith('cmd_')]

        rst = qtile_class_template.render(**context)
        for line in rst.splitlines():
            yield line


class QtileHooks(SimpleDirectiveMixin, Directive):
    def make_rst(self):
        module, class_name = self.arguments[0].rsplit('.', 1)
        obj = import_object(module, class_name)
        for method in obj.hooks:
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
            BaseClass = import_object(*self.arguments[
                self.arguments.index(':baseclass:') + 1].rsplit('.', 1))

        for item in dir(module):
            obj = import_object(self.arguments[0], item)
            if not isinstance(obj, class_types) and (BaseClass and
                not isinstance(obj, BaseClass)):
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


def setup(app):
    app.add_directive('qtile_class', QtileClass)
    app.add_directive('qtile_hooks', QtileHooks)
    app.add_directive('qtile_module', QtileModule)
