
========================
Installing on NixOS
========================

Qtile is available in the NixOS repos.
To set qtile as your window manager, include this in your configuration.nix file:

.. code-block:: nix

    services.xserver.windowManager.qtile.enable = true;

Other options for qtile can be declared within
the `services.xserver.windowManager.qtile` attribute set.

You may add extra packages in the qtile python environment by putting them
in the `extraPackages` list.

.. code-block:: nix

    services.xserver.windowManager.qtile = {
      enable = true;
      extraPackages = python3Packages: with python3Packages; [
        qtile-extras
      ];
    };

To enable the wayland backend, set the following option:

.. code-block:: nix

    # still in services.xserver.windowManager
    backend = "wayland";

If unspecified, it will default to `x11`.

The configuration file can be changed from its default location
(`$XDG_CONFIG/qtile/config.py`) by setting the `configFile` attribute:

.. code-block:: nix

    qtile = {
      enable = true;
      configFile = ./my_qtile_config.py;
    };

All option for qtile are listed on `search.nixos.org <https://search.nixos.org
/options?query=qtile>`__.
See the `module source <https://github.com/NixOS/nixpkgs/blob/master/nixos/
modules/services/x11/window-managers/qtile.nix>`__ for more details.

Home manager
************

If you are using home-manager, you can copy your qtile configuration
by using the following:

.. code-block:: nix

   home.file.qtile_config = {
     source = ./my_qtile_config.py;
     target = ".config/qtile/config.py";
   };

or, if you have a directory containing multiple python files:

.. code-block:: nix

   home.file.qtile_config = {
     source = ./src;
     target = ".config/qtile";
     recursive = true;
   };
