# Copyright (c) 2016 Sean Vig
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

import json
import os
import sys

from jupyter_client.kernelspec import install_kernel_spec
from tempfile import TemporaryDirectory

kernel_json = {
    "argv": [sys.executable, "-m", "libqtile.interactive.iqshell_kernel", "-f", "{connection_file}"],
    "display_name": "iqshell",
    "language": "qshell",
}


def main(argv=None):
    if argv is None:
        argv = []
    user = '--user' in argv or os.geteuid() != 0

    with TemporaryDirectory() as td:
        # IPython tempdir starts off as 700, not user readable
        os.chmod(td, 0o755)
        with open(os.path.join(td, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, sort_keys=True)

        print('Installing IPython kernel spec')
        install_kernel_spec(td, 'qshell', user=user, replace=True)


if __name__ == '__main__':
    main(sys.argv)
