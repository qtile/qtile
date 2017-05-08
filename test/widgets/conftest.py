import pytest

@pytest.fixture(scope='function')
def bar():
    from libqtile.bar import Bar
    height = 24
    b = Bar([], height)
    b.height = height
    return b
