import sys, os, inspect
sys.path.insert(0, ".")
import countershape.widgets
import countershape.layout
import countershape.markup
from countershape.doc import *
import cubictemp
import markdown2

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


class CmdObj:
    template = countershape.template.File(None, "_cmdobj.html")
    def __init__(self, o):
        parts = o.split(".")
        o = __import__("libqtile.layout", globals(), locals())
        for i in parts[1:]:
            o = getattr(o, i)
        self.parts = parts
        self.o = o

    @property
    def path(self):
        return ".".join(self.parts)
    
    @property
    def name(self):
        return self.parts[-1]

    @property
    def initargs(self):
        s = inspect.getargspec(getattr(self.o, "__init__"))
        return inspect.formatargspec(*s)

    @property
    def classdoc(self):
        return markdown2.markdown(inspect.getdoc(self.o) or "")

    @property
    def commands(self):
        l = []
        for i in sorted(dir(self.o)):
            if i.startswith("cmd_"):
                f = getattr(self.o, i)
                aspec = list(inspect.getargspec(f))
                aspec[0] = aspec[0][1:]
                a = inspect.formatargspec(*aspec)
                l.append(
                    [
                        i[4:] + a, 
                        markdown2.markdown(inspect.getdoc(f))
                    ]
                )
        return l

    @property
    def initdoc(self):
        s = getattr(self.o, "__init__")
        return inspect.getdoc(s)

    def __str__(self):
        return str(self.template(c=self))


this.markup = countershape.markup.Markdown()
ns.examples = Examples("..")
ns.cmdobj = CmdObj

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
