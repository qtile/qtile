"""
A helper script to set up Qtile's dependencies completely inside a virtualenv.
This removes the need to link to the libraries in the global site-packages and
allows updating dependencies without affecting the system Qtile install (if
you're using Qtile).

Note: This script is only intended for use during Qtile development.


Usage
=====

#.  Create a virtual environment for Qtile and activate it. (the script
    requires the virtual environment to be activated). For example, ::

      virtualenv --no-site-packages --distribute /some/path/qtile
      source /some/path/qtile/bin/activate

#.  Navigate to your Qtile development directory and run::

      python develop.py

    This will download the source, build (when required) and install all the
    dependencies, including the ones listed in the ``pip`` requirements file.
    When searching for the requirements file, assumes it's in the same
    directory as this script.

    The downloaded source code will be located at $VIRTUAL_ENV/src.


At least the following tools are required to build the dependencies (I may
have missed out a few):

*   git
*   pkgconfig
*   automake
*   autoconf
*   libtool
*   python 2.x (ideally python 2.7)
*   gperf
*   gtk-doc


The script has been tested using Python 2.7 on an Arch Linux box. For most of
the requirements, I used Arch Linux's ABS and AUR PKGBUILDS to obtain the
required steps.


"""

import subprocess as sp
import os

VENV = None
DEST_DIR = None


#==============================================================================
# Requirements start
#==============================================================================


def xorg_util_macros():
    url = 'git://anongit.freedesktop.org/git/xorg/util/macros'
    version = 'master'

    # ACLOCAL should only be set after xorg_util_macros is installed.
    aclocal = os.environ['ACLOCAL']
    export('ACLOCAL', '')

    get_git_src(url, 'xorg_util_macros', version)
    autogen()
    configure()
    make_make_install()

    export('ACLOCAL', aclocal)


def libxau():
    url = 'git://anongit.freedesktop.org/git/xorg/lib/libXau'
    version = 'master'

    get_git_src(url, 'libxau', version)
    autogen()
    configure()
    make_make_install()


def libxdmcp():
    url = 'git://anongit.freedesktop.org/git/xorg/lib/libXdmcp'
    version = 'master'

    get_git_src(url, 'libxdmcp', version)
    autogen()
    configure()
    make_make_install()


def pthread_stubs():
    url = 'git://anongit.freedesktop.org/git/xcb/pthread-stubs'
    version = 'master'

    get_git_src(url, 'pthread_stubs', version)
    autogen()
    configure()
    make_make_install()


def xcb_proto():
    url = 'git://anongit.freedesktop.org/git/xcb/proto'
    # http://groups.google.com/group/qtile-dev/browse_thread/thread/1a184316e991a119
    version = '661fe8dd7727c27467e61a0d20dc91557ce3747f'

    get_git_src(url, 'xcb_proto', version)
    autogen()
    configure()
    make_make_install()


def libxcb():
    url = 'git://anongit.freedesktop.org/git/xcb/libxcb'
    # master doesn't build against the specified xcb_proto version. Requires
    # recent xcb_proto version which we can't use.
    version = '8c2707773b3621fb8bbda9021d23944f5be34aab'
    # First commit that doesn't work: 80322d11636dd638902660d80481080d2fad40fe,
    # I think. Used git bisect.

    get_git_src(url, 'libxcb', version)
    autogen()
    configure('--enable-xinput')
    make_make_install()


def xcb_util():
    # http://aur.archlinux.org/packages/xc/xcb-util-git/PKGBUILD
    url = 'git://anongit.freedesktop.org/git/xcb/util'
    version = 'master'

    get_git_src(url, 'xcb_util', version, cloneargs=['--recursive'])
    autogen()
    configure()
    make_make_install()


def pixman():
    url = 'git://anongit.freedesktop.org/git/pixman.git'
    version = 'master'

    get_git_src(url, 'pixman', version)
    autogen()
    configure()
    make_make_install()


def cairo_xcb():
    # http://aur.archlinux.org/packages/ca/cairo-xcb/PKGBUILD
    url = 'git://anongit.freedesktop.org/git/cairo'
    version = 'master'

    get_git_src(url, 'cairo_xcb', version)
    autogen()
    configure('--enable-xcb')
    make_make_install()


def xpyb_ng():
    pip_install('-e git://github.com/dequis/xpyb-ng.git#egg=xpyb')


def py2cairo_xcb():
    # http://aur.archlinux.org/packages/py/pycairo-xcb-git/PKGBUILD
    url = 'git://git.cairographics.org/git/py2cairo'
    version = 'master'

    get_git_src(url, 'py2cairo_xcb', version)
    autogen()
    configure('--enable-xcb')
    make_make_install()


def pygobject():
    url = 'git://git.gnome.org/pygobject'
    version = 'PYGOBJECT_2_28_6'

    get_git_src(url, 'pygobject', version)
    autogen()
    configure('--disable-introspection')
    make_make_install()


def pygtk():
    url = 'git://git.gnome.org/pygtk'
    version = 'master'

    get_git_src(url, 'pygtk', version)
    autogen()
    configure()
    make_make_install()


def python_xlib():
    pip_install('http://downloads.sourceforge.net/python-xlib/python-xlib-0.15rc1.tar.gz')


def pip_requirements_file():
    os.chdir(os.path.abspath(__file__))
    pip_install('-r requirements.txt')


#==============================================================================
# Requirements end
#==============================================================================


def pip_install(*args):
    call('pip install {0}'.format(' '.join(args)))


def export(key, value):
    print 'export {0}={1}'.format(key, value)
    os.environ[key] = value


def get_git_src(url, destination, revision, cloneargs=[], checkoutargs=[]):
    # If directory exists checkout version, else clone and checkout version.
    d = dest(destination)
    if not os.path.exists(d):
        git_clone(url, d, *cloneargs)

    os.chdir(d)
    git_checkout(revision, *checkoutargs)


def git_clone(url, dest, *args):
    call('git clone {0} {1} {2}'.format(url, dest, ' '.join(args)))


def git_checkout(revision, *args):
    call('git checkout {0} {1}'.format(revision, ' '.join(args)))


def dest(d):
    return os.path.join(DEST_DIR, d)


def autogen(*args):
    call('./autogen.sh {0}'.format(' '.join(args)))


def configure(*args):
    call('./configure --prefix={0} {1}'.format(VENV, ' '.join(args)))


def make_make_install():
    call('make')
    call('make install')


def call(cmd):
    print cmd
    out = sp.call(cmd, shell=True)
    if out != 0:
        raise Exception('Ah! $@#%^&!! Error!!')
    return out


def main():
    global VENV
    global DEST_DIR

    # Assumes the virtualenv has been activated.
    VENV = os.environ['VIRTUAL_ENV']
    DEST_DIR = os.path.join(VENV, 'src')

    bin = os.path.join(VENV, 'bin')
    python = os.path.join(bin, 'python')
    lib = os.path.join(VENV, 'lib')
    pkgconfig = os.path.join(lib, 'pkgconfig')
    aclocal = os.path.join(VENV, 'share', 'aclocal')

    # All of Qtile's requirements, including those in the pip requirements
    # file. Order matters.
    reqs = [xorg_util_macros, libxau, libxdmcp, pthread_stubs, xcb_proto,
            libxcb, xcb_util, xpyb_ng, pixman, cairo_xcb, py2cairo_xcb,
            pygobject, pygtk, python_xlib, pip_requirements_file]

    export('ACLOCAL', 'aclocal -I {0}'.format(aclocal))
    export('PKG_CONFIG_PATH', pkgconfig)
    export('LD_LIBRARY_PATH', lib)
    export('PYTHON', python)

    for r in reqs:
        r()


if __name__ == '__main__':
    main()
