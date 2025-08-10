
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

The Qtile package creates desktop files for both X11 and Wayland,
to use one of the backends choose the right session in your display manager.

The configuration file can be changed from its default location
(`$XDG_CONFIG/qtile/config.py`) by setting the `configFile` attribute:

.. code-block:: nix

    qtile = {
      enable = true;
      configFile = ./my_qtile_config.py;
    };

.. note::

  Some options may change over time, please refer to see all the options for the latest stable:
  `search.nixos.org <https://search.nixos.org/options?channel=24.05&from=0&size=50&sort=relevance&type=packages&query=qtile>`__ if you have any doubt

Home manager
************

If you are using home-manager, you can copy your qtile configuration
by using the following:

.. code-block:: nix

   xdg.configFile."qtile/config.py".source = ./my_qtile_config.py;

or, if you have a directory containing multiple python files:

.. code-block:: nix

   xdg.configFile."qtile" = {
     source = ./src;
     recursive = true;
   };

Flake
*****

Qtile provides a Nix flake in its repository. This can be useful for:

- Running a bleeding-edge version of Qtile by specifying the flake input as the package.

- Hacking on Qtile using a Nix develop shell.

.. Note:: 

   Nix flakes are still an experimental NixOS feature, but they are already widely used. This section is intended for users who are already familiar with flakes.

To run a bleeding-edge version of Qtile with the flake, add the Qtile repository to your flake inputs and define the package. For example:


.. code-block:: nix

  {
    description = "A very basic flake";
    inputs = {
      nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";

      qtile-flake = {
        url = "github:qtile/qtile";
        inputs.nixpkgs.follows = "nixpkgs";
      };
    };

    outputs =
      {
        self,
        nixpkgs,
        qtile-flake,
      }:
      {
        nixosConfigurations.demo = nixpkgs.lib.nixosSystem {
          system = "x86_64-linux";

          modules = [
            (
              {
                config,
                pkgs,
                lib,
                ...
              }:
              {
                services.xserver = {
                  enable = true;
                  windowManager.qtile = {
                    enable = true;
                    package = qtile-flake.packages.${pkgs.system}.default;
                  };
                };

                # make qtile X11 the default session
                services.displayManager.defaultSession = lib.mkForce "qtile";

                # rest of your NixOS config
              }
            )
          ];
        };
      };
  }

This flake can also be tested with a vm:

.. code-block:: console

  sudo nixos-rebuild build-vm --flake .#demo

Gives you a script to run that runs Qemu to test your config. For this to work you have to set a user with a password.


To hack on Qtile with Nix, simply run `nix develop` in a checkout of the repo.
In the development shell, there are a few useful things:

- `qtile-run-tests-wayland`: Run all Wayland tests
- `qtile-run-tests-x11`: Run all X11 tests
