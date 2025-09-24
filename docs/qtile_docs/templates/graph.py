from jinja2 import Template

qtile_graph_template = Template(
    """
.. graphviz::
  :layout: neato
  :align: center
  {% for line in graph %}
  {{ line }}{% endfor %}

"""
)
