# Copyright (C) 2018, zordsdavini
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

from libqtile.extension.dmenu import Dmenu


class CommandSet(Dmenu):
    """
    Give list of commands to be executed in dmenu style.
    Commands can either be cmdline strings or callable functions.
    Functions take two argument: qtile object and select command string.

    ex. manage mocp deamon:

    .. code-block:: python

        Key([mod], 'm', lazy.run_extension(extension.CommandSet(
            commands={
                'play/pause': '[ $(mocp -i | wc -l) -lt 2 ] && mocp -p || mocp -G',
                'next': 'mocp -f',
                'previous': 'mocp -r',
                'quit': 'mocp -x',
                'open': 'urxvt -e mocp',
                'shuffle': 'mocp -t shuffle',
                'repeat': 'mocp -t repeat',
                },
            pre_commands=['[ $(mocp -i | wc -l) -lt 1 ] && mocp -S'],
            **Theme.dmenu))),


    ex. CommandSet inside another CommandSet

    .. code-block:: python

        CommandSet(
            commands={
                "Hello": CommandSet(
                    commands={
                        "World": "echo 'Hello, World!'"
                    },
                    **Theme.dmenu
                )
            },
        **Theme.dmenu
        )

    ex. CommandSet with callables

    .. code-block:: python

        def dynamic_group_addnew(qtile, command):
            name = f"special_{ command.lower() }"
            if name not in qtile.groups_map:
                qtile.addgroup(name, label=command, persist=False)
            qtile.groups_map[name].toscreen()

        CommandSet(
            pre_commands = [ 
              lambda self: # Pre-Commands are executed in extention context.
                setattr(
                   self,
                  "commands",
                  {
                    group.label: lambda qtile, name: qtile.groups_map[f"special_{name}"].toscreen()
                    for group in self.qtile.groups
                    if group.name.startswith("special_")
                  }
                )
            ],
            commands = {},
            unlisted = dynamic_group_addnew,
            **Theme.dmenu
        )

    """

    defaults = [
        ("unlisted", None, "An optional function to handle unlisted command keys."),
        ("commands", None, "dictionary of commands where key is runable command or a callable"),
        ("pre_commands", None, "list of commands to be executed before getting dmenu answer"),
    ]

    def __init__(self, **config):
        Dmenu.__init__(self, **config)
        self.add_defaults(CommandSet.defaults)

    def run(self):
        if not self.commands and not self.unlisted:
            return

        if self.pre_commands:
            for cmd in self.pre_commands:
                if isinstance(cmd,str):
                    self.qtile.spawn(cmd)
                elif callable(cmd):
                    cmd(self)

        out = super().run(items=self.commands.keys())

        try:
            sout = out.rstrip("\n")
        except AttributeError:
            # out is not a string (for example it's a Popen object returned
            # by super(WindowList, self).run() when there are no menu items to
            # list
            return

        command = self.commands.get(sout)
        if not command:
            if self.unlisted:
                self.unlisted(self.qtile, sout)
            return

        if isinstance(command, str):
            self.qtile.spawn(command)
        elif isinstance(command, CommandSet):
            command.run()
        elif callable(command):
            command(self.qtile, sout)
