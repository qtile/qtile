
========================
Installing on NixOS
========================

Qtile is available in the NixOS repos.
To set qtile as your window manager, include this in your configuration.nix file:

.. code-block:: bash

    services.xserver.windowManager.qtile.enable = true;
