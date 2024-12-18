self: final: prev: {
  pythonPackagesOverlays = (prev.pythonPackagesOverlays or [ ]) ++ [
    (_: pprev: {
      qtile =
        (pprev.qtile.overrideAttrs (
          old:
          let
            flakever = self.shortRev or "dev";

            releases = (
              builtins.filter (x: !builtins.isList x && prev.lib.strings.hasPrefix "Qtile" x) (
                builtins.split "\n" (builtins.readFile ../CHANGELOG)
              )
            );

            # the 0th element is the template
            current-release-title = builtins.elemAt releases 1;

            symver = builtins.head (
              builtins.match "Qtile ([0-9.]+), released ([0-9-]+):" current-release-title
            );

          in
          {
            version = "${symver}+${flakever}.flake";
            # use the source of the git repo
            src = ./..;
            # for qtile migrate, not in nixpkgs yet
            propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [
              pprev.libcst
              pprev.dbus-fast
            ];
            dependencies = prev.lib.filter (x: x != pprev.dbus-next) (old.propagatedBuildInputs or [ ]);
          }
        )).override
          {
            wlroots = prev.wlroots_0_17;
          };
    })
  ];
  python3 =
    let
      self = prev.python3.override {
        inherit self;
        packageOverrides = prev.lib.composeManyExtensions final.pythonPackagesOverlays;
      };
    in
    self;
  python3Packages = final.python3.pkgs;
}
