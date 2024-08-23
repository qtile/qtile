{
  description = "A flake for Qtile";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs, ... }: let 
    supportedSystems = ["x86_64-linux" "aarch64_linux"];
    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    nixpkgsFor = forAllSystems (system:
    import nixpkgs {
      inherit system;
        overlays = [(import ./nix/overlays.nix self)];
      });
  in {
    overlays = import ./nix/overlays.nix self;
    packages = forAllSystems (system: let
      pkgs = nixpkgsFor.${system};
    in {
      qtile = pkgs.python3.pkgs.qtile.overrideAttrs (_: {
        inherit (pkgs.python3.pkgs.qtile) pname version meta;
        name = with pkgs.python3.pkgs.qtile; "${pname}-${version}";
        passthru.unwrapped = pkgs.python3.pkgs.qtile;
      });
      default = self.packages.${system}.qtile;
    });

    devShells = forAllSystems (
      system: let
        pkgs = nixpkgsFor.${system};
        common-shell = {
          env = {
            QTILE_DLOPEN_LIBGOBJECT = "${pkgs.glib.out}/lib/libgobject-2.0.so.0";
            QTILE_DLOPEN_LIBPANGOCAIRO = "${pkgs.pango.out}/lib/libpangocairo-1.0.so.0";
            QTILE_DLOPEN_LIBPANGO = "${pkgs.pango.out}/lib/libpango-1.0.so.0";
            QTILE_DLOPEN_LIBXCBUTILCURSORS = "${pkgs.xcb-util-cursor.out}/lib/libxcb-cursor.so.0";
            QTILE_INCLUDE_LIBPIXMAN = "${pkgs.pixman.outPath}/include";
            QTILE_INCLUDE_LIBDRM = "${pkgs.libdrm.dev.outPath}/include/libdrm";
          };
          shellHook = ''
            export PYTHONPATH=$(readlink -f .):$PYTHONPATH
          '';
        };
        common-python-deps = ps:
          with ps; [
            # deps for running, same as NixOS package
            (cairocffi.override {withXcffib = true;})
            dbus-next
            iwlib
            mpd2
            psutil
            pulsectl-asyncio
            pygobject3
            python-dateutil
            pywayland
            pywlroots
            pyxdg
            xcffib
            xkbcommon

            # building ffi
            setuptools

            # migrate
            libcst

            # tests
            coverage
            pytest
          ];
        common-system-deps = with pkgs; [
          # Gdk namespaces
          wrapGAppsHook
          gobject-introspection

          ## system deps
          libinput
          libxkbcommon
          xorg.xcbutilwm

          # x11 deps
          xorg.xorgserver
          xorg.libX11

          # wayland deps
          wayland
          wlroots_0_17
          # test/backend/wayland/test_window.py
          gtk-layer-shell

          # some targets scripts run
          (
            pkgs.writeScriptBin "qtile-run-tests-wayland" ''
              ./scripts/ffibuild -v
              pytest -x --backend=wayland
            ''
          )

          (
            pkgs.writeScriptBin "qtile-run-tests-x11" ''
              ./scripts/ffibuild -v
              pytest -x --backend=x11
            ''
          )
        ];
      in {
        name = "default";
        value = pkgs.mkShell {
          packages =
            with pkgs; [
              (python3.withPackages (
                ps:
                  (common-python-deps ps)
              ))
              pre-commit
            ]
            ++ common-system-deps;
          inherit (common-shell) env shellHook;
        };
      }
    );
  };
}
