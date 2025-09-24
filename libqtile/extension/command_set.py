from libqtile.extension.dmenu import Dmenu


class CommandSet(Dmenu):
    """
    Give list of commands to be executed in dmenu style.

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

    """

    defaults = [
        ("commands", None, "dictionary of commands where key is runable command"),
        ("pre_commands", None, "list of commands to be executed before getting dmenu answer"),
    ]

    def __init__(self, **config):
        Dmenu.__init__(self, **config)
        self.add_defaults(CommandSet.defaults)

    def run(self):
        if not self.commands:
            return

        if self.pre_commands:
            for cmd in self.pre_commands:
                self.qtile.spawn(cmd)

        out = super().run(items=self.commands.keys())

        try:
            sout = out.rstrip("\n")
        except AttributeError:
            # out is not a string (for example it's a Popen object returned
            # by super(WindowList, self).run() when there are no menu items to
            # list
            return

        if sout not in self.commands:
            return

        command = self.commands[sout]

        if isinstance(command, str):
            self.qtile.spawn(command)
        elif isinstance(command, CommandSet):
            command.run()
