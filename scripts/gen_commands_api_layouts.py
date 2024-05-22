"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

layouts = [
    # Page name, page name, layout class.
    ("Bsp", "bsp.md", "libqtile.layout.bsp.Bsp"),
    ("Columns", "columns.md", "libqtile.layout.columns.Columns"),
    ("Floating", "floating.md", "libqtile.layout.floating.Floating"),
    ("Matrix", "matrix.md", "libqtile.layout.matrix.Matrix"),
    ("Max", "max.md", "libqtile.layout.max.Max"),
    ("MonadTall", "monadtall.md", "libqtile.layout.xmonad.MonadTall"),
    ("MonadThreeCol", "monadthreecol.md", "libqtile.layout.xmonad.MonadThreeCol"),
    ("MonadWide", "monadwide.md", "libqtile.layout.xmonad.MonadWide"),
    ("Plasma", "plasma.md", "libqtile.layout.plasma.Plasma"),
    ("RatioTile", "ratiotile.md", "libqtile.layout.ratiotile.RatioTile"),
    ("ScreenSplit", "screensplit.md", "libqtile.layout.screensplit.ScreenSplit"),
    ("Slice", "slice.md", "libqtile.layout.slice.Slice"),
    ("Spiral", "spiral.md", "libqtile.layout.spiral.Spiral"),
    ("Stack", "stack.md", "libqtile.layout.stack.Stack"),
    ("Tile", "tile.md", "libqtile.layout.tile.Tile"),
    ("TreeTab", "treetab.md", "libqtile.layout.tree.TreeTab"),
    ("VerticalTile", "verticaltile.md", "libqtile.layout.verticaltile.VerticalTile"),
    ("Zoomy", "zoomy.md", "libqtile.layout.zoomy.Zoomy"),
]

for name, page, path in layouts:
    doc_path = Path("manual/commands/api/layouts", page)
    nav[name] = page
    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"---\ntitle: {name}\n---\n\n::: {path}")
    module_path = path.rsplit(".", 1)[0].replace(".", "/")
    mkdocs_gen_files.set_edit_path(doc_path, f"../{module_path}.py")

with mkdocs_gen_files.open("manual/commands/api/layouts/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
