import sys, os
sys.path.insert(0, "..")
import countershape.widgets
import countershape.layout
import countershape.grok
from countershape.doc import *
from libqtile import manager, layout, bar

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

ns.examples = Examples("..")

ns.docTitle = "Qtile 0.2"
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@nullcube.com"
ns.foot = "Copyright Aldo Cortesi 2008"
ns.head = readFrom("_header.html")
ns.sidebar = countershape.widgets.SiblingPageIndex('/index.html')
this.layout = countershape.layout.TwoPane("yui-t2", "doc3")
this.titlePrefix = "Qtile 0.2 - "

ns.qtgrok = countershape.grok.grok("../libqtile")

pages = [
    Page("index.html", "Introduction"),
    Page("objects.html", "Object Graph"),
    Directory("objects"),
    Page("configuration.html", "Configuration"),
    Directory("configuration"),
    Page("scripting.html", "Scripting"),
    Page("qsh.html", "qsh - The Qtile Shell"),
    Page("dev.html", "Hacking on Qtile"),
    Page("faq.html", "FAQ"),
    Page("admin.html", "Administrivia")
]
