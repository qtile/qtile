import pytest

import libqtile
from libqtile.widget import generic_poll_text


def test_gen_poll_text():
    gpt_no_func = generic_poll_text.GenPollText()
    assert gpt_no_func.poll() == "You need a poll function"

    gpt_with_func = generic_poll_text.GenPollText(func=lambda: "Has function")
    assert gpt_with_func.poll() == "Has function"


@pytest.mark.asyncio
async def test_gen_poll_url_not_configured():
    gpurl = generic_poll_text.GenPollUrl()
    assert await gpurl.apoll() == "Invalid config"


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


@pytest.mark.asyncio
async def test_gen_poll_url_text(httpbin):
    gpurl = generic_poll_text.GenPollUrl(
        json=False, parse=lambda x: x, url=f"{httpbin.url}/anything"
    )
    result = await gpurl.apoll()
    assert isinstance(result, str)
    assert "anything" in result


@pytest.mark.asyncio
async def test_gen_poll_url_json_with_data(httpbin):
    gpurl = generic_poll_text.GenPollUrl(
        parse=lambda x: x["data"], data={"test": "value"}, url=f"{httpbin.url}/anything"
    )
    result = await gpurl.apoll()
    assert result == '{"test": "value"}'


@pytest.mark.asyncio
async def test_gen_poll_url_xml_no_xmltodict(httpbin):
    gpurl = generic_poll_text.GenPollUrl(
        json=False, xml=True, parse=lambda x: x, url=f"{httpbin.url}/anything"
    )
    result = await gpurl.apoll()
    assert result == "Can't parse"


@pytest.mark.asyncio
async def test_gen_poll_url_broken_parse(httpbin):
    gpurl = generic_poll_text.GenPollUrl(
        json=False, parse=lambda x: x.foo, url=f"{httpbin.url}/anything"
    )
    result = await gpurl.apoll()
    assert result == "Can't parse"


@pytest.mark.asyncio
async def test_gen_poll_url_custom_headers(httpbin):
    gpurl = generic_poll_text.GenPollUrl(
        headers={"X-Custom-Header": "test-value", "X-Another-Header": "another-value"},
        parse=lambda x: x["headers"],
        url=f"{httpbin.url}/headers",
    )
    result = await gpurl.apoll()
    assert "X-Custom-Header" in result
    assert result["X-Custom-Header"] == "test-value"
    assert "X-Another-Header" in result
    assert result["X-Another-Header"] == "another-value"


def test_gen_poll_command(manager_nospawn, minimal_conf_noscreen):
    gpcommand = generic_poll_text.GenPollCommand(cmd=["echo", "hello"])
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([gpcommand], 10))]
    manager_nospawn.start(config)
    command = manager_nospawn.c.widget["genpollcommand"]
    assert command.info()["text"] == "hello"
