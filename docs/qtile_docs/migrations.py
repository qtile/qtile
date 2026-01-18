from docutils.parsers.rst import Directive, directives

from libqtile.scripts.migrations import MIGRATIONS, load_migrations
from qtile_docs.base import SimpleDirectiveMixin
from qtile_docs.templates import qtile_migrations_full_template, qtile_migrations_template


class QtileMigrations(SimpleDirectiveMixin, Directive):
    """
    A custom directive that is used to display details about the
    migrations available to `qtile migrate`.
    """

    required_arguments = 0
    option_spec = {
        "summary": directives.flag,
        "help": directives.flag,
    }

    def make_rst(self):
        load_migrations()

        context = {"migrations": [(m, len(m.ID)) for m in MIGRATIONS]}

        if "summary" in self.options:
            rst = qtile_migrations_template.render(**context)
        elif "help" in self.options:
            rst = qtile_migrations_full_template.render(**context)

        yield from rst.splitlines()
