self: final: prev:
let
  inherit (prev) pkgs lib;

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

  qtile-override-func =
    qtile-prev:
    {
      name = "${qtile-prev.pname}-${qtile-prev.version}";

      version = local-version;

      src = ./..; # use the source of the git repo
    }
    // {
      propagatedBuildInputs =
        (qtile-prev.propagatedBuildInputs or [ ]) ++ (with pkgs.python3Packages; [ aiohttp ]);

      env = build-config.resolved-env-vars;

      pypaBuildFlags = build-config.resolved-config-settings;
    }
    // {
      # removes nixpkgs patching, as we handle it locally
      postPatch = "";

      patches = [ ];
    };
in
{
  pythonPackagesOverlays = (prev.pythonPackagesOverlays or [ ]) ++ [
    (
      _: py-prev:
      let
        qtile = py-prev.qtile.overrideAttrs qtile-override-func;
      in
      {
        qtile = qtile.override { wlroots = pkgs.wlroots_0_17; };
      }
    )
  ];

  python3 = prev.python3.override {
    self = final.python3;
    packageOverrides = lib.composeManyExtensions final.pythonPackagesOverlays;
  };

  python3Packages = final.python3.pkgs;
}
