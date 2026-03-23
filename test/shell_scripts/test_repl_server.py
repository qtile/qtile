from libqtile.interactive.repl import get_completions


def test_get_completions_top_level():
    local_vars = {"qtile": "dummy", "qtiles": 123}
    result = get_completions("qti", local_vars)
    assert "qtile" in result
    assert "qtiles" in result


def test_get_completions_attribute():
    class Dummy:
        def method(self):
            pass

        val = 42

    local_vars = {"dummy": Dummy()}
    result = get_completions("dummy.me", local_vars)
    assert "dummy.method(" in result

    result = get_completions("dummy.va", local_vars)
    assert "dummy.val" in result


def test_get_completions_invalid_expr():
    result = get_completions("invalid..expr", {})
    assert result == []
