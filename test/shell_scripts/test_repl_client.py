# Copyright (c) 2025 elParaguayo
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
import pytest

from libqtile.scripts.repl import TERMINATOR, is_code_complete, read_full_response


class MockSocket:
    def recv(self, *args, **kwargs):
        return (f"Qtile test\nREPL client\n{TERMINATOR}\n").encode()


def test_read_full_response_basic():
    # Create a mock socket with recv method
    sock = MockSocket()

    response = read_full_response(sock)
    assert "Qtile test" in response
    assert "REPL client" in response
    # The terminator should be stripped off
    assert TERMINATOR not in response


@pytest.mark.parametrize(
    "input,valid",
    [
        ("x+1", True),
        ("def a():", False),
        ("def a():\n  print(1)", False),
        ("def a():\n  print(1)\n", True),
        ("def a():\n  print(1)\ndef b():\n  print(2)\n", True),
        ("while True:\n", False),
    ],
    ids=[
        "SingleExpression",
        "IncompleteFunction",
        "MultilineIncomplete",
        "MultilineComplete",
        "MultiMultiline",
        "IncompleteContext",
    ],
)
def test_is_code_complete(input, valid):
    assert is_code_complete(f"{input}\n") is valid
