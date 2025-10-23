{
  description = "Qtile's flake, full-featured, hackable tiling window manager written and configured in Python";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
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
          sphinx_rtd_theme

          # tests
          coverage
          pytest
          isort
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
          wrapGAppsHook
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

        pkgs-wrapped = pkgs.lib.lists.flatten [
          common-python-deps
          common-system-deps
          (builtins.attrValues tests)
        ];
      });
    in
    {
      formatter = forAllSystems (pkgs: pkgs.nixfmt-rfc-style);

      checks = forAllSystems (pkgs: pkgs.python3Packages.qtile.passthru.tests);

      packages = forAllSystems (pkgs: {
        default = self.packages.${pkgs.system}.qtile;

        qtile = import ./nix/qtile.nix { inherit pkgs self; };
      });

      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          env = flake-attributes.${pkgs.system}.shell-env;

          inputsFrom = [ self.packages.${pkgs.system}.qtile ];
          packages = flake-attributes.${pkgs.system}.pkgs-wrapped;
        };
      });
    };
}
