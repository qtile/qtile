{ pkgs, ... }:
{
  pre-commit-config =
    let
      inherit (pkgs) lib;

      mypyEnv = pkgs.python3.withPackages (
        ps: with ps; [
          mypy
          types-python-dateutil
          types-pytz
        ]
      );

      hooks = {
        ruff-check = {
          entry = "${lib.getExe pkgs.ruff} check";
          types = "[python]";
        };
        ruff-format = {
          entry = "${lib.getExe pkgs.ruff} format";
          types = "[python]";
        };
        mypy = {
          entry = "${lib.getExe' mypyEnv "mypy"} --ignore-missing-imports --scripts-are-modules";
          types = "[python]";
        };
        clang-format = {
          entry = "${lib.getExe' pkgs.clang-tools "clang-format"} -i";
          types_or = "[c, c++]";
        };
      };

      rewrite =
        line:
        let
          hook = builtins.match "( *)- id: (.*)" line;
        in
        if (lib.hasInfix "repo: https://" line) then
          [ "  - repo: local" ]
        else if (builtins.match " *(rev|additional_dependencies):.*" line != null) then
          [ ]
        else if (hook != null) then
          let
            indent = builtins.elemAt hook 0 + "  ";
            id = builtins.elemAt hook 1;
            h = hooks.${id} or (throw "pre-commit hook '${id}' has no Nix entry in flake.nix");
          in
          [
            line
            "${indent}name: ${id}"
            "${indent}language: system"
          ]
          ++ lib.mapAttrsToList (k: v: "${indent}${k}: ${v}") h
        else
          [ line ];
    in
    pkgs.writeText "pre-commit-config-nix.yaml" (
      lib.concatStringsSep "\n" (
        lib.concatMap rewrite (lib.splitString "\n" (builtins.readFile ../.pre-commit-config.yaml))
      )
    );
}
