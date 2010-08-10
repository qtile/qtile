import sys, os
sys.path.insert(0, "..")
import countershape.widgets
import countershape.layout
import countershape.markup
from countershape.doc import *

class Examples:
    def __init__(self, d):
        self.d = os.path.abspath(d)

    def _wrap(self, proc, path):
        f = file(os.path.join(self.d, path)).read()
        if proc:
            f = proc(f)
        post = "<div class=\"fname\">(%s)</div>"%path
        return f + post

    def py(self, path, **kwargs):
        return self._wrap(ns.pySyntax.withConf(**kwargs), path)

this.markup = countershape.markup.Markdown()
ns.examples = Examples("..")

ns.docTitle = "Qtile 0.4"
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@nullcube.com"
ns.foot = "Copyright Aldo Cortesi 2010"
ns.version = "0.4"
ns.sidebar = countershape.widgets.SiblingPageIndex('/index.html')
ns.copyright = "Copyright (c) 2010 Aldo Cortesi"
this.layout = countershape.Layout("_layout.html")
this.titlePrefix = "Qtile %s - "%ns.version


pages = [
    Page("index.html", "Introduction"),
    Page("configuration.html", "Configuration"),
    Directory("configuration"),
    Page("objects.html", "Object Graph"),
    Page("scripting.html", "Scripting"),
    Page("qsh.html", "qsh - the Qtile shell"),
    Page("dev.html", "Hacking on Qtile"),
    Page("faq.html", "FAQ"),
    Page("admin.html", "Administrivia")
]
