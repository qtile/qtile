# Copyright (c) 2023 elParaguayo
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
