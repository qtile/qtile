import pytest

from libqtile.scripts.repl import is_code_complete


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
