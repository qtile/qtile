{
  pkgs,
  self,
}:
let
  inherit (pkgs) lib;

  build-config = import ./build-config.nix pkgs;

  local-version =
    with builtins;
    let
      flakever = self.shortRev or "dev";

      symver = lib.pipe (readFile ../CHANGELOG) [
        (split "\n")
        (filter (x: !isList x && lib.strings.hasPrefix "Qtile" x))
        (release: elemAt release 1) # the 0th element is the template
        (match "Qtile ([0-9.]+), released ([0-9-]+):")
        head
      ];
    in
    "${symver}+${flakever}.flake";

  removeOldDeps =
    dep:
    !(pkgs.lib.hasAttr "pname" dep)
    || (
      dep.pname != pkgs.python3Packages.pywlroots.pname
      && dep.pname != pkgs.python3Packages.pywayland.pname
      && dep.pname != pkgs.python3Packages.xkbcommon.pname
    );

  qtile-override-func =
    qtile-prev:
    {
      name = "${qtile-prev.pname}-${qtile-prev.version}";

      version = local-version;

      src = ./..; # use the source of the git repo
    }
    // {
      env = build-config.resolved-env-vars;

      propagatedBuildInputs =
        (with pkgs; [
          wayland-scanner
          wayland-protocols
          python3Packages.cffi
          python3Packages.xcffib
          python3Packages.aiohttp
        ])
        ++ (lib.filter removeOldDeps qtile-prev.propagatedBuildInputs);

      pypaBuildFlags = [ "--config-setting=backend=wayland" ] ++ build-config.resolved-config-settings;
    }
    // {
      # removes nixpkgs patching, as we handle it locally
      postPatch = "";

      patches = [ ];
    };
in
(pkgs.python3Packages.qtile.overrideAttrs qtile-override-func).override {
  wlroots = pkgs.wlroots_0_19;
}
