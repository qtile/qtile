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
import re
from os.path import expanduser
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from libqtile.layout.serialize import (
    LayoutSerDes,
    SerializedLayout,
    SerializedWindow,
    WindowSerDes,
)


def test_resolve_to_absolute_path():
    # layout name should resolve to an absolute path
    path = LayoutSerDes.resolve_path("test")
    assert path.is_absolute()
    assert path.name == "test.json"
    assert path.parent.name == "layouts"
    assert path.parent.parent.name == "qtile"


def test_resolve_given_absolute_path():
    # absolute paths should be used as is
    path = Path("/tmp/test.json")
    resolved_path = LayoutSerDes.resolve_path(path)
    assert path == resolved_path


def test_resolve_expand_user_path():
    # ~ should be expaned to user
    path = Path("~/test.json")
    resolved_path = LayoutSerDes.resolve_path(path)
    assert str(resolved_path).startswith(expanduser("~"))


@pytest.fixture
def serialized_layout():
    return SerializedLayout(name="test")


layout_filenames = pytest.mark.parametrize("name", [("test"), ("/tmp/test.json")])


@layout_filenames
def test_save_serialized_layout(serialized_layout, name):
    with patch("pathlib.Path.open", mock_open()) as mock_file:
        LayoutSerDes.save_to(serialized_layout, name)

        saved_json = json.loads(
            "\n".join([call.args[0] for call in mock_file().write.call_args_list])
        )
        assert serialized_layout == saved_json


@layout_filenames
def test_load_serialized_layout(serialized_layout, name):
    with patch("pathlib.Path.open", mock_open(read_data=json.dumps(serialized_layout))) as _:
        loaded_json = LayoutSerDes.load_from(name)
        assert serialized_layout == loaded_json


@layout_filenames
def test_load_serialized_layout_check_name_fail(serialized_layout, name):
    with patch("pathlib.Path.open", mock_open(read_data=json.dumps(serialized_layout))) as _:
        with pytest.raises(RuntimeError):
            LayoutSerDes.load_from(name, check_layout_name=serialized_layout["name"][::-1])


def test_serialized_window_no_fields():
    # all fields should be optional
    SerializedWindow()


@pytest.fixture
def serialized_window_all_kwargs():
    fields = ["title", "wm_instance_class", "wm_class", "role", "wm_type"]
    fields.extend([f"{field}_regex" for field in fields])

    kwargs = {v: v for v in fields}
    kwargs["net_wm_pid"] = 0
    kwargs["focus"] = True

    return kwargs


def test_serialized_window_all_fields(serialized_window_all_kwargs):
    serialized_window = SerializedWindow(**serialized_window_all_kwargs)

    for key in serialized_window_all_kwargs:
        assert serialized_window[key] == serialized_window_all_kwargs[key]


@patch("libqtile.layout.serialize.Match")
def test_serialized_window_to_match(mock_match):
    kwargs = {v: v for v in ["title", "wm_class", "wm_class_regex"]}
    kwargs["focus"] = True

    WindowSerDes.to_match(SerializedWindow(**kwargs))

    assert mock_match.call_count == 1

    call_kwargs = mock_match.call_args.kwargs
    assert call_kwargs["title"] == kwargs["title"]
    assert call_kwargs.get("wm_instance_class", None) is None
    assert call_kwargs["wm_class"] == re.compile(kwargs["wm_class_regex"])
    assert call_kwargs.get("role", None) is None
    assert call_kwargs.get("wm_type", None) is None
    assert call_kwargs.get("net_wm_pid", None) is None
    assert call_kwargs.get("focus", None) is None
