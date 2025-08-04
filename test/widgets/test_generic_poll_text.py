# Copyright (c) 2021 elParaguayo
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

# Widget specific tests

import sys
from importlib import reload
from types import ModuleType

import pytest

import libqtile
from libqtile.widget import generic_poll_text


class Mockxml(ModuleType):
    @classmethod
    def parse(cls, value):
        return {"test": value}


class MockRequest:
    return_value = None

    def __init__(self, *args, **kwargs):
        pass


class Mockurlopen:
    def __init__(self, request):
        self.request = request

    class headers:  # noqa: N801
        @classmethod
        def get_content_charset(cls):
            return "utf-8"

    def read(self):
        return self.request.return_value


def test_gen_poll_text():
    gpt_no_func = generic_poll_text.GenPollText()
    assert gpt_no_func.poll() == "You need a poll function"

    gpt_with_func = generic_poll_text.GenPollText(func=lambda: "Has function")
    assert gpt_with_func.poll() == "Has function"


def test_gen_poll_url_not_configured():
    gpurl = generic_poll_text.GenPollUrl()
    assert gpurl.poll() == "Invalid config"


def test_gen_poll_url_no_json():
    gpurl = generic_poll_text.GenPollUrl(json=False)
    assert "Content-Type" not in gpurl.headers


def test_gen_poll_url_headers_and_json():
    gpurl = generic_poll_text.GenPollUrl(
        headers={"fake-header": "fake-value"},
        data={"argument": "data value"},
        user_agent="qtile test",
    )

    assert gpurl.headers["User-agent"] == "qtile test"
    assert gpurl.headers["fake-header"] == "fake-value"
    assert gpurl.headers["Content-Type"] == "application/json"
    assert gpurl.data.decode() == '{"argument": "data value"}'


def test_gen_poll_url_text(monkeypatch):
    gpurl = generic_poll_text.GenPollUrl(json=False, parse=lambda x: x, url="testing")
    monkeypatch.setattr(generic_poll_text, "Request", MockRequest)
    monkeypatch.setattr(generic_poll_text, "urlopen", Mockurlopen)
    generic_poll_text.Request.return_value = b"OK"
    assert gpurl.poll() == "OK"


def test_gen_poll_url_json(monkeypatch):
    gpurl = generic_poll_text.GenPollUrl(parse=lambda x: x, data=[1, 2, 3], url="testing")
    monkeypatch.setattr(generic_poll_text, "Request", MockRequest)
    monkeypatch.setattr(generic_poll_text, "urlopen", Mockurlopen)
    generic_poll_text.Request.return_value = b'{"test": "OK"}'
    assert gpurl.poll()["test"] == "OK"


def test_gen_poll_url_xml_no_xmltodict(monkeypatch):
    gpurl = generic_poll_text.GenPollUrl(json=False, xml=True, parse=lambda x: x, url="testing")
    monkeypatch.setattr(generic_poll_text, "Request", MockRequest)
    monkeypatch.setattr(generic_poll_text, "urlopen", Mockurlopen)
    generic_poll_text.Request.return_value = b"OK"
    with pytest.raises(Exception):
        gpurl.poll()


def test_gen_poll_url_xml_has_xmltodict(monkeypatch):
    # injected fake xmltodict module but we have to reload the widget module
    # as the ImportError test is only run once when the module is loaded.
    monkeypatch.setitem(sys.modules, "xmltodict", Mockxml("xmltodict"))
    reload(generic_poll_text)
    gpurl = generic_poll_text.GenPollUrl(json=False, xml=True, parse=lambda x: x, url="testing")
    monkeypatch.setattr(generic_poll_text, "Request", MockRequest)
    monkeypatch.setattr(generic_poll_text, "urlopen", Mockurlopen)
    generic_poll_text.Request.return_value = b"OK"
    assert gpurl.poll()["test"] == "OK"


def test_gen_poll_url_broken_parse(monkeypatch):
    gpurl = generic_poll_text.GenPollUrl(json=False, parse=lambda x: x.foo, url="testing")
    monkeypatch.setattr(generic_poll_text, "Request", MockRequest)
    monkeypatch.setattr(generic_poll_text, "urlopen", Mockurlopen)
    generic_poll_text.Request.return_value = b"OK"
    assert gpurl.poll() == "Can't parse"


def test_gen_poll_command(manager_nospawn, minimal_conf_noscreen):
    gpcommand = generic_poll_text.GenPollCommand(cmd=["echo", "hello"])
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([gpcommand], 10))]
    manager_nospawn.start(config)
    command = manager_nospawn.c.widget["genpollcommand"]
    assert command.info()["text"] == "hello"
