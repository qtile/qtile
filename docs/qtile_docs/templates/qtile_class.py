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
from jinja2 import Template

qtile_class_template = Template(
    """
{{ class_name }}
{{ class_underline }}

.. autoclass:: {{ module }}.{{ class_name }}{% for arg in extra_arguments %}
    {{ arg }}{% endfor %}
    :noindex:

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
    **Configuration options**

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

    **Available commands**

    Click to view the available commands for :py:class:`{{ class_name }} <{{ obj.__module__ }}.{{ class_name }}>`
    {% endif %}

"""
)
