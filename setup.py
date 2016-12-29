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

              - Ensure a recent xcffib is installed (pip install 'xcffib>=0.3.2')
              - The pip cache is cleared (remove ~/.cache/pip, if it exists)
              - Reinstall cairocffi, either:

                  pip install --no-deps --ignore-installed cairocffi

                or

                  pip uninstall cairocffi && pip install cairocffi
            """))

            sys.exit(1)
        install.finalize_options(self)

long_description = """
A pure-Python tiling window manager.

Features
========

    * Simple, small and extensible. It's easy to write your own layouts,
      widgets and commands.
    * Configured in Python.
    * Command shell that allows all aspects of
      Qtile to be managed and inspected.
    * Complete remote scriptability - write scripts to set up workspaces,
      manipulate windows, update status bar widgets and more.
    * Qtile's remote scriptability makes it one of the most thoroughly
      unit-tested window mangers around.
"""

if '_cffi_backend' in sys.builtin_module_names:
    import _cffi_backend
    requires_cffi = "cffi==" + _cffi_backend.__version__
else:
    requires_cffi = "cffi>=1.1.0"

# PyPy < 2.6 compatibility
if requires_cffi.startswith("cffi==0."):
    cffi_args = dict(
        zip_safe=False
    )
else:
    cffi_args = dict(cffi_modules=[
        'libqtile/ffi_build.py:pango_ffi',
        'libqtile/ffi_build.py:xcursors_ffi'
    ])

dependencies = ['xcffib>=0.3.2', 'cairocffi>=0.7', 'six>=1.4.1', requires_cffi]

if sys.version_info >= (3, 4):
    pass
elif sys.version_info >= (3, 3):
    dependencies.append('asyncio')
else:
    dependencies.append('trollius')

setup(
    name="qtile",
    version="0.10.6",
    description="A pure-Python tiling window manager.",
    long_description=long_description,
    classifiers=[
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: Unix",
        "Topic :: Desktop Environment :: Window Managers",
    ],
    keywords="qtile tiling window manager",
    author="Aldo Cortesi",
    author_email="aldo@nullcube.com",
    maintainer="Tycho Andersen",
    maintainer_email="tycho@tycho.ws",
    url="http://qtile.org",
    license="MIT",
    install_requires=dependencies,
    setup_requires=dependencies,
    extras_require={
        'ipython': ["ipykernel", "jupyter_console"],
    },
    packages=['libqtile',
              'libqtile.interactive',
              'libqtile.layout',
              'libqtile.scripts',
              'libqtile.widget',
              'libqtile.extention',
              'libqtile.resources'
              ],
    package_data={'libqtile.resources': ['battery-icons/*.png']},
    entry_points={
        'console_scripts': [
            'qtile = libqtile.scripts.qtile:main',
            'qtile-run = libqtile.scripts.qtile_run:main',
            'qtile-top = libqtile.scripts.qtile_top:main',
            'qshell = libqtile.scripts.qshell:main',
        ]
    },
    scripts=[
        'bin/iqshell',
    ],
    data_files=[
        ('share/man/man1', ['resources/qtile.1',
                            'resources/qshell.1'])],
    cmdclass={'install': CheckCairoXcb},
    **cffi_args
)
