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

import warnings

from .columns import Columns


class Wmii(Columns):
    """This layout is deprecated in favor of `Columns`.

    The only difference between the two are the default parameters.
    """
    defaults = [
        ("name", "wmii", "Name of this layout."),
        ("border_focus_stack", "#0000ff",
         "Border colour for the focused window in stacked columns."),
        ("border_normal_stack", "#000022",
         "Border colour for un-focused windows in stacked columns."),
        ("num_columns", 1, "Preferred number of columns."),
        ("insert_position", 1,
         "Position relative to the current window where new ones are inserted "
         "(0 means right above the current window, 1 means right after)."),
    ]

    def __init__(self, **config):
        warnings.warn(
            "Wmii layout is deprecated in favor of Columns.",
            category=DeprecationWarning,
            stacklevel=2)
        for key, value, _ in Wmii.defaults:
            config.setdefault(key, value)
        Columns.__init__(self, **config)
