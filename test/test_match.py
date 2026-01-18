import re

import pytest

from libqtile import layout
from libqtile.config import Match, Screen
from libqtile.confreader import Config


@pytest.fixture(scope="function")
def manager(manager_nospawn, request):
    class MatchConfig(Config):
        rules = getattr(request, "param", list())
        if not isinstance(rules, list | tuple):
            rules = [rules]

        screens = [Screen()]
        floating_layout = layout.Floating(float_rules=[*rules])

    manager_nospawn.start(MatchConfig)

    yield manager_nospawn


def configure_rules(*args):
    return pytest.mark.parametrize("manager", [args], indirect=True)


def assert_float(manager, name, floating=True):
    manager.test_window(name)
    assert manager.c.window.info()["floating"] is floating
    manager.c.window.kill()


@configure_rules(Match(title="floatme"))
@pytest.mark.parametrize(
    "name,result", [("normal", False), ("floatme", True), ("floatmetoo", False)]
)
def test_single_rule(manager, name, result):
    """Single string must be exact match"""
    assert_float(manager, name, result)


@configure_rules(Match(title=re.compile(r"floatme")))
@pytest.mark.parametrize(
    "name,result", [("normal", False), ("floatme", True), ("floatmetoo", True)]
)
def test_single_regex_rule(manager, name, result):
    """Regex to match substring"""
    assert_float(manager, name, result)


@configure_rules(~Match(title="floatme"))
@pytest.mark.parametrize(
    "name,result", [("normal", True), ("floatme", False), ("floatmetoo", True)]
)
def test_not_rule(manager, name, result):
    """Invert match rule"""
    assert_float(manager, name, result)


@configure_rules(Match(title="floatme") | Match(title="floating"))
@pytest.mark.parametrize(
    "name,result",
    [("normal", False), ("floatme", True), ("floating", True), ("floatmetoo", False)],
)
def test_or_rule(manager, name, result):
    """Invert match rule"""
    assert_float(manager, name, result)


@configure_rules(Match(title=re.compile(r"^floatme")) & Match(title=re.compile(r".*too$")))
@pytest.mark.parametrize(
    "name,result", [("normal", False), ("floatme", False), ("floatmetoo", True)]
)
def test_and_rule(manager, name, result):
    """Combine match rules"""
    assert_float(manager, name, result)


@configure_rules(Match(title=re.compile(r"^floatme")) ^ Match(title=re.compile(r".*too$")))
@pytest.mark.parametrize(
    "name,result",
    [("normal", False), ("floatme", True), ("floatmetoo", False), ("thisfloatstoo", True)],
)
def test_xor_rule(manager, name, result):
    """Combine match rules"""
    assert_float(manager, name, result)
