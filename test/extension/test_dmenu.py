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
from libqtile.extension.base import _Extension
from libqtile.extension.dmenu import Dmenu, DmenuRun, J4DmenuDesktop

BLACK = "#000000"


def test_dmenu_configuration_options():
    """
    Test that configuration options are correctly translated into
    command options for dmenu.
    """
    _Extension.global_defaults = {}

    opts = [
        ({}, ["dmenu"]),
        ({"dmenu_command": "testdmenu --test-option"}, ["testdmenu", "--test-option"]),
        ({"dmenu_command": ["testdmenu", "--test-option"]}, ["testdmenu", "--test-option"]),
        ({}, ["-fn", "sans"]),
        ({"dmenu_font": "testfont"}, ["-fn", "testfont"]),
        ({"font": "testfont"}, ["-fn", "testfont"]),
        ({"font": "testfont", "fontsize": 12}, ["-fn", "testfont-12"]),
        ({"dmenu_bottom": True}, ["-b"]),
        ({"dmenu_ignorecase": True}, ["-i"]),
        ({"dmenu_lines": 5}, ["-l", "5"]),
        ({"dmenu_prompt": "testprompt"}, ["-p", "testprompt"]),
        ({"background": BLACK}, ["-nb", BLACK]),
        ({"foreground": BLACK}, ["-nf", BLACK]),
        ({"selected_background": BLACK}, ["-sb", BLACK]),
        ({"selected_foreground": BLACK}, ["-sf", BLACK]),
        ({"dmenu_height": 100}, ["-h", "100"]),
    ]

    # Loop over options, create an instance of Dmenu with the provided "config"
    # find the index of the first item in "output" and check any following items
    # match the expected output
    for config, output in opts:
        extension = Dmenu(**config)
        extension._configure(None)
        index = extension.configured_command.index(output[0])
        assert output == extension.configured_command[index : index + len(output)]


def test_dmenu_run(monkeypatch):
    def fake_popen(cmd, *args, **kwargs):
        class PopenObj:
            def communicate(self, value_in, *args):
                return [value_in, None]

        return PopenObj()

    monkeypatch.setattr("libqtile.extension.base.Popen", fake_popen)

    # dmenu_lines is set to the lower of config value and len(items) so set a high value now
    extension = Dmenu(dmenu_lines=5)
    extension._configure(None)

    items = ["test1", "test2"]
    assert extension.run(items) == "test1\ntest2\n"

    # dmenu_lines should be length of items
    assert extension.configured_command[-2:] == ["-l", "2"]


def test_dmenurun_extension():
    extension = DmenuRun()
    assert extension.dmenu_command == "dmenu_run"


def test_j4dmenu_configuration_options():
    """
    Test that configuration options are correctly translated into
    command options for dmenu.
    """
    _Extension.global_defaults = {}

    opts = [
        ({}, ["j4-dmenu-desktop", "--dmenu"]),
        ({"font": "testfont"}, ["dmenu -fn testfont"]),  # Dmenu settings are applied too
        ({"j4dmenu_use_xdg_de": True}, ["--use-xdg-de"]),
        ({"j4dmenu_display_binary": True}, ["--display-binary"]),
        ({"j4dmenu_generic": False}, ["--no-generic"]),
        ({"j4dmenu_terminal": "testterminal"}, ["--term", "testterminal"]),
        ({"j4dmenu_usage_log": "testlog"}, ["--usage-log", "testlog"]),
    ]

    # Loop over options, create an instance of J4DmenuDesktop with the provided "config"
    # find the index of the first item in "output" and check any following items
    # match the expected output
    for config, output in opts:
        extension = J4DmenuDesktop(**config)
        extension._configure(None)
        index = extension.configured_command.index(output[0])
        print(extension.configured_command)
        assert output == extension.configured_command[index : index + len(output)]
