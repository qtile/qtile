#!/usr/bin/env python

# Copyright (c) 2008 Aldo Cortesi
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2012 dmpayton
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 roger
# Copyright (c) 2014 Pedro Algarvio
# Copyright (c) 2014-2015 Tycho Andersen
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

import sys
import textwrap

from setuptools import setup
from setuptools.command.install import install


class CheckCairoXcb(install):
    def cairo_xcb_check(self):
        try:
            from cairocffi import cairo
            cairo.cairo_xcb_surface_create
            return True
        except AttributeError:
            return False

    def finalize_options(self):
        if not self.cairo_xcb_check():

            print(textwrap.dedent("""

            It looks like your cairocffi was not built with xcffib support.  To fix this:

              - Ensure a recent xcffib is installed (pip install 'xcffib>=0.5.0')
              - The pip cache is cleared (remove ~/.cache/pip, if it exists)
              - Reinstall cairocffi, either:

                  pip install --no-deps --ignore-installed cairocffi

                or

                  pip uninstall cairocffi && pip install cairocffi
            """))

            sys.exit(1)
        install.finalize_options(self)


setup(
    cmdclass={'install': CheckCairoXcb},
    cffi_modules=[
        'libqtile/pango_ffi_build.py:pango_ffi',
        'libqtile/core/xcursors_ffi_build.py:xcursors_ffi',
    ],
)
