from jinja2 import Template

qtile_migrations_template = Template(
    """
.. list-table::
  :widths: 30 20 50
  :header-rows: 1

  * - ID
    - Changes introduced after version
    - Summary
{% for m, _ in migrations %}
  * - `{{ m.ID }}`_
    - {{ m.AFTER_VERSION }}
    - {{ m.SUMMARY }}
{% endfor %}
"""
)


qtile_migrations_full_template = Template(
    """
{% for m, len in migrations %}
{{ m.ID }}
{{ "~" * len }}

.. list-table::

  * - Migration introduced after version
    - {{ m.AFTER_VERSION}}

{{ m.show_help() }}

{% endfor %}

"""
)
