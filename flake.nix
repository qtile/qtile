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
        function:
        nixpkgs.lib.genAttrs supportedSystems (
          system:
          let
            nixpkgs-settings = {
              inherit system;

              overlays = [ (import ./nix/overlays.nix self) ];
            };
          in
          function (import nixpkgs nixpkgs-settings)
        );
    in
    {
      formatter = forAllSystems (pkgs: pkgs.nixfmt-rfc-style);

      checks = forAllSystems (pkgs: pkgs.python3Packages.qtile.passthru.tests);

      overlays.default = import ./nix/overlays.nix self;

      packages = forAllSystems (
        pkgs:
        let
          qtile' = pkgs.python3Packages.qtile;
        in
        {
          default = self.packages.${pkgs.system}.qtile;

          qtile = qtile'.overrideAttrs (prev: {
            name = "${qtile'.pname}-${qtile'.version}";
            passthru.unwrapped = qtile';
          });
        }
      );

      devShells = forAllSystems (
        pkgs:
        let
          common-python-deps =
            ps:
            with ps;
            [ python-dateutil ]
            ++ [
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
              ./scripts/ffibuild -v
              pytest -x --backend=wayland
            '';

            x11 = pkgs.writeScriptBin "qtile-run-tests-x11" ''
              ./scripts/ffibuild -v
              pytest -x --backend=x11
            '';
          };

          common-system-deps =
            with pkgs;
            [
              # Gdk namespaces
              wrapGAppsHook
              gobject-introspection

              # docs graphs
              graphviz

              # x11 deps
              xorg.xorgserver
              xorg.libX11

              wlroots_0_17
              # test/backend/wayland/test_window.py
              gtk-layer-shell
              imagemagick
            ]
            ++ (builtins.attrValues tests);
        in
        {
          default = pkgs.mkShell {
            env = {
              QTILE_PIXMAN_PATH = "${pkgs.pixman}/include/pixman-1";
              QTILE_LIBDRM_PATH = "${pkgs.libdrm.dev}/include/libdrm";

              LD_LIBRARY_PATH =
                with pkgs;
                lib.makeLibraryPath [
                  glib
                  pango
                  xcb-util-cursor
                  pixman
                  libdrm.dev
                ];
            };

            shellHook = ''
              export PYTHONPATH=$(readlink -f .):$PYTHONPATH
            '';

            inputsFrom = [ self.packages.${pkgs.system}.qtile ];

            packages =
              with pkgs;
              [
                (python3.withPackages common-python-deps)
                pre-commit
              ]
              ++ common-system-deps;
          };
        }
      );
    };
}
