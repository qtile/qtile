pkgs:
let
  # library to be provided using the `--config-setting`
  runtime-libs = [
    {
      varname = "GOBJECT";
      pkg = pkgs.glib;
      libname = "libgobject-2.0.so";
    }
    {
      varname = "PANGO";
      pkg = pkgs.pango;
      libname = "libpango-1.0.so";
    }
    {
      varname = "PANGOCAIRO";
      pkg = pkgs.pango;
      libname = "libpangocairo-1.0.so";
    }
    {
      varname = "XCBCURSOR";
      pkg = pkgs.xorg.xcbutilcursor;
      libname = "libxcb-cursor.so";
    }
  ];

  # header files provided through environment variables
  headers-location = [
    {
      varname = "PIXMAN";
      pkg = pkgs.pixman;
      header-dir = "pixman-1";
    }
    {
      varname = "LIBDRM";
      pkg = pkgs.libdrm;
      header-dir = "libdrm";
    }
  ];

  # Internal implementation
  inherit (pkgs) lib;
in
{
  resolved-config-settings = map (
    {
      varname,
      pkg,
      libname,
    }:
    "--config-setting=${varname}=${lib.getLib pkg}/lib/${libname}"
  ) runtime-libs;

  resolved-env-vars = lib.foldr (a: b: a // b) { } (
    map (
      {
        varname,
        pkg,
        header-dir,
      }:
      {
        "QTILE_${varname}_PATH" = "${lib.getDev pkg}/include/${header-dir}";
      }
    ) headers-location
  );
}
