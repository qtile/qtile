# Copyright (c) 2016, Sean Vig
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

from ipykernel.kernelbase import Kernel
from libqtile import command, sh


class QshKernel(Kernel):
    implementation = 'qshell'
    implementation_version = '0.1'
    language = 'no-op'
    language_version = '1.0'
    language_info = {'mimetype': 'text/plain'}
    banner = "Qsh Kernel"

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.client = command.Client()
        self.qsh = sh.QSh(self.client)

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        # if no command sent, just return
        if not code.strip():
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }

        if code[-1] == '?':
            return self.do_inspect(code, len(code) - 1)

        try:
            output = self.qsh.process_command(code)
        except KeyboardInterrupt:
            return {
                'status': 'abort',
                'execution_count': self.execution_count,
            }

        if not silent and output:
            stream_content = {'name': 'stdout', 'text': output}
            self.send_response(self.iopub_socket, 'stream', stream_content)

        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }

    def do_complete(self, code, cursor_pos):
        no_complete = {
            'status': 'ok',
            'matches': [],
            'cursor_start': 0,
            'cursor_end': cursor_pos,
            'metadata': dict(),
        }

        if not code or code[-1] == ' ':
            return no_complete

        tokens = code.split()
        if not tokens:
            return no_complete

        token = tokens[-1]
        start = cursor_pos - len(token)

        matches = self.qsh._complete(code, token)
        return {
            'status': 'ok',
            'matches': sorted(matches),
            'cursor_start': start,
            'cursor_end': cursor_pos,
            'metadata': dict(),
        }


def main():
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=QshKernel)


if __name__ == '__main__':
    main()
