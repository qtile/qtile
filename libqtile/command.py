# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

import os
import warnings

from .utils import get_cache_dir

from libqtile.command_client import InteractiveCommandClient
from libqtile.lazy import LazyCommandObject


SOCKBASE = "qtilesocket.%s"


def find_sockfile(display=None):
    """
        Finds the appropriate socket file.
    """
    display = display or os.environ.get('DISPLAY') or ':0.0'
    if '.' not in display:
        display += '.0'
    cache_directory = get_cache_dir()
    return os.path.join(cache_directory, SOCKBASE % display)


class _LazyTree(InteractiveCommandClient):
    def __getattr__(self, *args, **kwargs):
        warnings.warn("libqtile.command.lazy is deprecated, use libqtile.lazy.lazy", DeprecationWarning)
        return super().__getattr__(*args, **kwargs)


lazy = _LazyTree(LazyCommandObject())
