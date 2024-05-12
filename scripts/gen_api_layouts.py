"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

exclude = {"__init__.py", "base.py"}
root = Path(__file__).parent.parent
src = root

docs_dir = Path("manual", "commands", "api", "layouts")

for path in sorted(src.rglob("libqtile/layout/*.py")):
    if path.name in exclude:
        continue
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.with_suffix(".md").name
    full_doc_path = docs_dir / doc_path

    parts = tuple(module_path.parts)
    nav[parts[-1]] = doc_path

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"---\ntitle: {ident}\n---\n\n::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, ".." / path.relative_to(root))

with mkdocs_gen_files.open(docs_dir / "SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
