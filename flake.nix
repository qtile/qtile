{
  description = "Qtile's flake, full-featured, hackable tiling window manager written and configured in Python";
  inputs = {
    # This pins the flake to a previous version. This is added at the moment
    # in this pull request as a temporary fix to allow running of all tests
    # from this flakes development shell. After figuring out what is causing
    # the issue in the newest version, this SHOULD BE REMOVED BEFORE MERGING.
    nixpkgs.url = "github:nixos/nixpkgs?ref=01f116e4df6a15f4ccdffb1bcd41096869fb";
  };
  outputs =
    {
      self,
      nixpkgs,
    }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      forAllSystems =
        f: nixpkgs.lib.genAttrs supportedSystems (system: f nixpkgs.legacyPackages.${system});

      flake-attributes = forAllSystems (pkgs: rec {
        build-config = import ./nix/build-config.nix pkgs;

        common-python-deps = with pkgs.python3Packages; [
          python-dateutil

          # docs building
          numpydoc
          sphinx
          sphinx-rtd-theme

          # tests
          coverage
          pytest
          isort
          pytest-asyncio
          anyio
          pytest-httpbin
        ];

        tests = {
          wayland = pkgs.writeScriptBin "qtile-run-tests-wayland" ''
            pytest -x --backend=wayland
          '';
          x11 = pkgs.writeScriptBin "qtile-run-tests-x11" ''
            pytest -x --backend=x11
          '';
        };

        common-system-deps = with pkgs; [
          # Gdk namespaces
          wrapGAppsHook3
          gobject-introspection

          # docs graphs
          graphviz

          # generating compile_commands.json
          bear

          # clang-format for formatting
          clang-tools

          # test/backend/wayland/test_window.py
          gtk-layer-shell
          imagemagick

          pre-commit
        ];

        shell-env = {
          LD_LIBRARY_PATH =
            with pkgs;
            lib.makeLibraryPath [
              glib
              pango
              xcb-util-cursor
              pixman
              libdrm.dev
            ];
        }
        // build-config.resolved-env-vars;

        qtile-final = self.packages.${pkgs.stdenv.hostPlatform.system}.qtile;

        pkgs-wrapped =
          pkgs.lib.lists.flatten [
            common-python-deps
            common-system-deps
            (builtins.attrValues tests)
          ]
          ++ [ qtile-final ];
      });
    in
    {
      formatter = forAllSystems (pkgs: pkgs.nixfmt-rfc-style);

      checks = forAllSystems (pkgs: pkgs.python3Packages.qtile.passthru.tests);

      packages = forAllSystems (pkgs: {
        default = self.packages.${pkgs.stdenv.hostPlatform.system}.qtile;

        qtile = import ./nix/qtile.nix { inherit pkgs self; };
      });

      devShells = forAllSystems (
        pkgs:
        let
          flake-attrs = flake-attributes.${pkgs.stdenv.hostPlatform.system};
        in
        {
          default = pkgs.mkShell {
            env = flake-attrs.shell-env;

            inputsFrom = [ flake-attrs.qtile-final ];
            packages = flake-attrs.pkgs-wrapped;
          };
        }
      );
    };
}
