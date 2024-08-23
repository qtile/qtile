self: final: super: {
  pythonPackagesOverlays =
    (super.pythonPackagesOverlays or [])
    ++ [
      (_: pprev: {
        pywlroots = (pprev.pywlroots.overrideAttrs(_: rec {
          version = "0.17.0";
          src = super.fetchFromGitHub {
            owner = "flacjacket";
            repo = "pywlroots";
            rev = "bf314bae5d7a9552225c44ab1e7bf7e4fafa869e";
            hash = "sha256-tvem8gmih9EfseZ3MgU1UW05xfttzKLcJEaymM5uNPI=";
          };
        })).override {
          wlroots = super.wlroots_0_17;
        };
        qtile = (pprev.qtile.overrideAttrs (old: let
          flakever = self.shortRev or "dev";
        in {
          version = "0.0.0+${flakever}.flake";
          # use the source of the git repo
          src = ./..;
          # for qtile migrate, not in nixpkgs yet
          propagatedBuildInputs = old.propagatedBuildInputs ++ [ pprev.libcst ];
        })).override {
          wlroots = super.wlroots_0_17;
        };
      })
    ];
  python3 = let
    self = super.python3.override {
      inherit self;
      packageOverrides = super.lib.composeManyExtensions final.pythonPackagesOverlays;
    };
  in
    self;
  python3Packages = final.python3.pkgs;
}


