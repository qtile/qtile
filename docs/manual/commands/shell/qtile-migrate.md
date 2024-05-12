qtile migrate
=============

``qtile migrate`` is a tool to help users update their configs to
reflect any breaking changes/deprecations introduced in later versions.

The tool can automatically apply updates but it can also be used to highlight
impacted lines, allowing users to update their configs manually.

The tool can take a number of options when running:

.. list-table::
    :widths: 10 45 45
    :header-rows: 1

    * - Argument
      - Description
      - Default
    * - ``-c``, ``--config``
      - Sets the path to the config file
      - ``~/.config/qtile/config.py``
    * - ``--list-migrations``
      - Lists all the available migrations that can be
        run by the tool.
      - n/a
    * - ``--info ID``
      - Show more detail about the migration implement by
        ID.
      - n/a
    * - ``--after-version VERSION``
      - Only runs migrations relating to changes implemented
        after release VERSION.
      - Not set (i.e. runs all migrations).
    * - ``-r ID``, ``--run-migrations ID``
      - Run selected migrations identified by ID. Comma separated
        list if using multiple values.
      - Not set (i.e. runs all migrations).
    * - ``--yes``
      - Automatically apply changes without asking user for confirmation.
      - Not set (i.e. users will need to confirm application 
        of changes).
    * - ``--show-diff``
      - When used with ``--yes`` will cause diffs to still be shown for
        information purposes only.
      - Not set.
    * - ``--no-colour``
      - Disables colour output for diff.
      - Not set
    * - ``--lint``
      - Outputs linting lines showing location of changes.
        No changes are made to the config.
      - Not set.

Available migrations
--------------------

The following migrations are currently available.

.. qtile_migrations::
  :summary:

Running migrations
------------------

Assuming your config file is in the default location, running ``qtile migrate``
is sufficent to start the migration process.

Let's say you had a config file with the following contents:

.. code:: python

  import libqtile.command_client

  keys = [
      KeyChord(
          [mod],
          "x",
          [Key([], "Up", lazy.layout.grow()), Key([], "Down", lazy.layout.shrink())],
          mode="Resize layout",
      )
  ]

  qtile.cmd_spawn("alacritty")

Running ``qtile migrate`` will run each available migration and, where the migration would
result in changes, a diff will be shown and you will be asked whether you wish to apply the changes.

.. code:: 

  UpdateKeychordArgs: Updates ``KeyChord`` argument signature.

  --- original
  +++ modified
  @@ -5,7 +5,8 @@

          [mod],
          "x",
          [Key([], "Up", lazy.layout.grow()), Key([], "Down", lazy.layout.shrink())],
  -        mode="Resize layout",
  +        name="Resize layout",
  +    mode=True,
      )
  ]

  Apply changes? (y)es, (n)o, (s)kip file, (q)uit.

You will see from the output above that you are shown the name of the migration being
applied and its purpose, along with the changes that will be implemented.

If you select ``quit`` the migration will be stopped and any applied changes will
be reversed.

Once all migrations have been run on a file, you will then be asked whether you want
to save changes to the file:

.. code::

  Save all changes to config.py? (y)es, (n)o.

At the end of the migration, backups of your original config will still
be in your config folder. NB these will be overwritten if you re-run
``qtile migrate``.

Linting
-------

If you don't want the script to modify your config directly, you can use
the ``--lint`` option to show you where changes are required.

Running ``qtile migrate --lint`` on the same config as shown above will result
in the following output:

.. code::

  config.py:
  [Ln 1, Col 7]: The 'libqtile.command_*' modules have been moved to 'libqtile.command.*'. (ModuleRenames)
  [Ln 8, Col 8]: The use of mode='mode name' for KeyChord is deprecated. Use mode=True and value='mode name'. (UpdateKeychordArgs)
  [Ln 12, Col 6]: Use of 'cmd_' prefix is deprecated. 'cmd_spawn' should be replaced with 'spawn' (RemoveCmdPrefix)

Explanations of migrations
--------------------------

The table below provides more detail of the available migrations.

.. qtile_migrations::
  :help:
