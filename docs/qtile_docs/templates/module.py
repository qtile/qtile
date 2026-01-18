from jinja2 import Template

qtile_module_template = Template(
    """
.. qtile_class:: {{ module }}.{{ class_name }}
    {% if no_config %}:no-config:{% endif %}
    {% if no_commands %}:no-commands:{% endif %}
"""
)
