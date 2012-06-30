Hooks
=====

Qtile provides a mechanism for subscribing to certain events in
``libqtile.hook``. To subscribe to a hook in your configuration, simply decorate a function with
the hook you wish to subscribe to.

Let's say we wanted to automatically float all dialog windows. We would
subscribe to the ``client_new`` hook to tell us when a new window has opened
and, if the type is "dialog", as can set the window to float. In our
configuration file it would look something like this:

.. code-block:: python

    from libqtile import hook

    @hook.subscribe.client_new
    def floating_dialogs(window):
        dialog = window.window.get_wm_type() == 'dialog'
        transient = window.window.get_wm_transient_for()
        if dialog or transient:
            window.floating = True

A list of available hooks can be found in the
:doc:`Built-in Hooks </manual/ref/hooks>` reference.
