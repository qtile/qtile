from jinja2 import Template

qtile_commands_template = Template(
    """
{% if not no_title %}
{{ baseclass }}
{{ underline }}
{% endif %}

.. py:currentmodule:: {{ module }}

.. py:class:: {{ baseclass }}

  **API commands**

  To access commands on this object via the command graph, use one of the following
  options:

  .. list-table::

    * - {{ interfaces["lazy"] }}
    * - {{ interfaces["cmdobj"] }}

  The following commands are available for this object:

  .. autosummary::

  {% for cmd in commands %}
    {{ cmd }}
  {% endfor %}

  **Command documentation**

  {% for cmd in commands %}
  .. automethod:: {{ cmd }}

  {% endfor %}

"""
)
