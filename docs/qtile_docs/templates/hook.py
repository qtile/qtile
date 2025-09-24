from jinja2 import Template

qtile_hooks_template = Template(
    """
.. automethod:: libqtile.hook.subscribe.{{ method }}
"""
)
