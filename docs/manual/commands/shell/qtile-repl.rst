==========
qtile repl
==========

Creates a REPL (Read-Evaluate-Print-Loop) client with access to the qtile internals.

The client requires the `prompt_toolkit <https://pypi.org/project/prompt_toolkit/>`__
library to work.

The client has support for code completion, multiline input and input history.

Running ``qtile repl`` will start the server with access to the ``qtile`` instance. However, users can
add extra items to the REPL's environment by starting the REPL server from their config before
launching the client e.g.:

.. code-block:: python

    keys = [
        ...,
        Key([mod], "z", lazy.start_repl_server(locals_dict=globals())),
        ...
    ]

This will add all variables from a user's config to the REPL environment, allowing users to
trigger their own functions etc.

The REPL server runs on port 41414. This is hardcoded for now but we expect to make changes to
qtile's wire format in the future.
