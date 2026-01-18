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
