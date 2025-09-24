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
