How to write a migration script
===============================

Qtile's migration scripts should provide two functions:

* Update config files to fix any breaking changes introduced by a commit
* Provide linting summary of errors in existing configs

To do this, we use `LibCST <https://libcst.readthedocs.io/en/latest/>`_ to
parse the config file and make changes as appropriate. Basic tips for using
``LibCST`` are included below but it is recommended that you read their
documentation to familiarise yourself with the available functionalities.

Stucture of a migration file
----------------------------

Migrations should be saved as a new file in ``libqtile/scripts/migrations``.

A basic migration will look like this:

.. code:: python

    from libqtile.scripts.migrations._base import MigrationTransformer, _QtileMigrator, add_migration


    class MyMigration(MigrationTransformer):
        """The class that actually modifies the code."""
        ...


    class Migrator(_QtileMigrator):
        ID = "MyMigrationName"

        SUMMARY = "Summary of migration."

        HELP = """
        Longer text explaining purpose of the migration and, ideally,
        giving code examples.

        """

        AFTER_VERSION = "0.22.1"

        TESTS = []

        visitor = MyMigration


    add_migration(Migrator)

Providing details about the migration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The purpose of ``Migrator`` class in the code above is to provide the information about the migration.

It is important that the information is as helpful as possible as it is used in multiple places.

* The ``ID`` attribute is a short, unique name to identify the migration. This allows users to select
  specific migrations to run via ``qtile migrate --run-migrations ID``.
* The ``SUMMARY`` attribute is used to provide a brief summary of the migration and is used when
  a user runs ``qtile migrate --list-migrations``. It is also used in the documentation.
* Similarly, the ``HELP`` attribute is used for the script (``qtie migrate --info ID``) and the
  documentation. This text should be longer and can include example code. As it is used in the documentation,
  it should use RST syntax (e.g. ``.. code:: python`` for codeblocks etc.).
* ``AFTER_VERSION`` should be set the name of the current release. This allows users to filter migrations to
  those that were added after the last release.
* The ``visitor`` attribute is a link to the class definition (not and instance of the class) for the
  transformer that you wish to use.
* The ``add_migration`` call at the end is required to ensure the migration is loaded into the list of
  available migrations.
* See below for details on ``TESTS``.

How migrations are run
~~~~~~~~~~~~~~~~~~~~~~

You are pretty much free to transform the code as you see fit. By default, the script will run the
``visit`` method on the parsed code and will pass the ``visitor`` attribute of the ``_QtileMigrator`` class
object. Therefore, if all your transformations can be performed in a single visitor, it is not necessary
to do anything further in the ``Migrator`` class.

However, if you want to run mutiple visitors, transformers, codemods, this is possible by overriding the
``run`` method of the ``_QtileMigrator`` class. For example, the ``RemoveCmdPrefix`` migrator has the following
code:

.. code:: python

    def run(self, original):
        # Run the base migrations
        transformer = CmdPrefixTransformer()
        updated = original.visit(transformer)
        self.update_lint(transformer)

        # Check if we need to add an import line
        if transformer.needs_import:
            # We use the built-in visitor to add the import
            context = codemod.CodemodContext()
            AddImportsVisitor.add_needed_import(
                context, "libqtile.command.base", "expose_command"
            )
            visitor = AddImportsVisitor(context)

            # Run the visitor over the updated code
            updated = updated.visit(visitor)

        return original, updated

In this migration, it may be required to add an import statement. ``LibCST`` has a built-in
transformation for doing this so we can run that after our own transformation has been performed.

.. important::

    The ``run`` method must return a tuple of the original code and the updated code.

Transforming the code
~~~~~~~~~~~~~~~~~~~~~

It is recommended that you use a `transformed <https://libcst.readthedocs.io/en/latest/tutorial.html#Build-Visitor-or-Transformer>`_
to update the code. For convenience, a ``MigrationTransformer`` class is defined in ``libqtile.scripts.migrations._base``. This
class definition includes some metadata information and a ``lint`` method for outputting details of errors.

Let's look at an example transformer to understand how the migration works. The code below shows how to change a positional
argument to a keyword argument in the ``WidgetBox`` widget.

.. code:: python

    class WidgetboxArgsTransformer(MigrationTransformer):
        @m.call_if_inside(
            m.Call(func=m.Name("WidgetBox")) | m.Call(func=m.Attribute(attr=m.Name("WidgetBox")))
        )
        @m.leave(m.Arg(keyword=None))
        def update_widgetbox_args(self, original_node, updated_node) -> cst.Arg:
            """Changes positional  argumentto 'widgets' kwargs."""
            self.lint(
                original_node,
                "The positional argument should be replaced with a keyword argument named 'widgets'.",
            )
            return updated_node.with_changes(keyword=cst.Name("widgets"), equal=EQUALS_NO_SPACE)

Our class (which inherits from ``MigrationTransformer``) defines a single method to perform the transformation. We take
advantage of ``LibCST`` and its `Matchers <https://libcst.readthedocs.io/en/latest/matchers_tutorial.html>`_ to narrow the
scope of when the transformation is run.

We are looking to modify an argument so we use the ``@m.leave(m.Arg())`` decorator to call the function at end of parsing an
argument. We can restrict when this is called by specify ``m.Arg(keyword=None)`` so that it is only called for positional arguments.
Furthermore, as we only want this called for ``WidgetBox`` instantiation lines, we add an additional decorator
``@m.call_if_inside(m.Call())``. This ensures the method is only called when we're in a call. On its own, that's not helpful as args
would  almost always be part of a call. However, we can say we only want to match calls to ``WidgetBox``. The reason for the long syntax above is
that ``LibCST`` parses ``WidgetBox()`` and ``widget.WidgetBox()`` differently. In the first one, ``WidgetBox`` is in the ``func`` property of the call.
However, in the second, the ``func`` is an ``Attribute`` as it is a dotted name and so we need to check the ``attr`` property.

The decorated method takes two arguments, ``original_mode`` and ``updated_node`` (note: The ``original_node`` should not be modified).
The method should also confirm the return type.

The above method provides a linting message by calling ``self.lint`` and passing the original node and a helpful message.

Finally, the method updates the code by calling ``updated_node.with_changes()``. In this instance, we add a keyword (``"widgets"``) to
the argument. We also remove spaces around the equals sign as these are added by default by ``LibCST``. The updated node is returned.

Helper classes
~~~~~~~~~~~~~~

Helper classes are provided for common transformations.

* ``RenamerTransformer`` will update all instances of a name, replacing it with another. The class will
  also handle the necessary linting.

  .. code:: python

    class RenameHookTransformer(RenamerTransformer):
        from_to = ("window_name_change", "client_name_updated")

Testing the migration
~~~~~~~~~~~~~~~~~~~~~

All migrations must be tested, ideally with a number of scenarios to confirm that the migration
works as expected.

Unlike other tests, the tests for the migrations are defined within the ``TESTS`` attribute.

This is a list that should take a ``Check``, ``Change`` or ``NoChange`` object (all are imported from
``libqtile.scripts.migrations._base``).

A ``Change`` object needs two parameters, the input code and the expected output. A ``NoChange``
object just defines the input (as the output should be the same).

A ``Check`` object is identical to ``Change`` however, when running the test suite, the migrated
code will be verified with ``qtile check``. The code will therefore need to include all relevant
imports etc.

Based on the above, the following is recommended as best practice:

* Define one ``Check`` test which addresses every situation anticipated by the migration
* Use as many ``Change`` tests as required to test individual scenarios in a minimal way
* Use ``NoChange`` tests where there are specific cases that should not be modified
* Depending on the simplicity of the migration, a single ``Check`` may be all that is required

For example, the ``RemoveCmdPrefix`` migration has the following ``TESTS``:

.. code:: python

    TESTS = [
        Change("""qtile.cmd_spawn("alacritty")""", """qtile.spawn("alacritty")"""),
        Change("""qtile.cmd_groups()""", """qtile.get_groups()"""),
        Change("""qtile.cmd_screens()""", """qtile.get_screens()"""),
        Change("""qtile.current_window.cmd_hints()""", """qtile.current_window.get_hints()"""),
        Change(
            """qtile.current_window.cmd_opacity(0.5)""",
            """qtile.current_window.set_opacity(0.5)""",
        ),
        Change(
            """
            class MyWidget(widget.Clock):
                def cmd_my_command(self):
                    pass
            """,
            """
            from libqtile.command.base import expose_command

            class MyWidget(widget.Clock):
                @expose_command
                def my_command(self):
                    pass
            """
        ),
        NoChange(
            """
            def cmd_some_other_func():
                pass
            """
        ),
        Check(
            """
            from libqtile import qtile, widget

            class MyClock(widget.Clock):
                def cmd_my_exposed_command(self):
                    pass

            def my_func(qtile):
                qtile.cmd_spawn("rickroll")
                hints = qtile.current_window.cmd_hints()
                groups = qtile.cmd_groups()
                screens = qtile.cmd_screens()
                qtile.current_window.cmd_opacity(0.5)

            def cmd_some_other_func():
                pass
            """,
            """
            from libqtile import qtile, widget
            from libqtile.command.base import expose_command

            class MyClock(widget.Clock):
                @expose_command
                def my_exposed_command(self):
                    pass

            def my_func(qtile):
                qtile.spawn("rickroll")
                hints = qtile.current_window.get_hints()
                groups = qtile.get_groups()
                screens = qtile.get_screens()
                qtile.current_window.set_opacity(0.5)

            def cmd_some_other_func():
                pass
            """
        )
    ]

The tests check:

* ``cmd_`` prefix is removed on method calls, updating specific changes as required
* Exposed methods in a class should use the ``expose_command`` decorator (adding the import if it's not already included)
* No change is made to a function definition (as it's not part of a class definition)

.. note::
    
    Tests will fail in the following scenarios:
    
    * If no tests are defined
    * If a ``Change`` test does not result in linting output
    * If no ``Check`` test is defined

You can check your tests by running ``pytest -k <YourMigrationID>``. Note, ``mpypy`` must be installed for the
``Check`` tests to be run.
