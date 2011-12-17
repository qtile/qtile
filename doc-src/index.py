import sys
import os
import inspect
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
        post = "<div class=\"fname\">(%s)</div>" % path
        return f + post

    def py(self, path, **kwargs):
        return self._wrap(ns.pySyntax.withConf(**kwargs), path)


class _Obj:
    def __init__(self, o, image=None):
        self.image = image
        parts = o.split(".")
        o = __import__(".".join(parts[:-1]), globals(), locals())
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
    def defaults(self):
        d = getattr(self.o, "defaults", None)
        if d:
            return d.defaults
        else:
            return d

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
                        markdown2.markdown(inspect.getdoc(f) or "")
                    ]
                )
        return l

    @property
    def methods(self):
        """
            Returns a list of dicts describing methods.
        """
        l = []
        for i in sorted(dir(self.o)):
            if not i.startswith("_"):
                f = getattr(self.o, i)
                l.append(
                    dict(
                        name=i,
                        doc=markdown2.markdown(
                            inspect.getdoc(f) or "")
                    )
                )
        return l

    @property
    def initdoc(self):
        s = getattr(self.o, "__init__")
        return markdown2.markdown(inspect.getdoc(s) or "")

    def __str__(self):
        return str(self.template(c=self))


class ConfObj(_Obj):
    template = countershape.template.File(None, "_configobj.html")


class CmdObj(_Obj):
    template = countershape.template.File(None, "_cmdobj.html")


class HookObj(_Obj):
    template = countershape.template.File(None, "_hookobj.html")


this.markup = countershape.markup.Markdown()
ns.examples = Examples("..")
ns.confobj = ConfObj
ns.cmdobj = CmdObj
ns.hookobj = HookObj

ns.docTitle = "Qtile 0.4"
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@nullcube.com"
ns.foot = "Copyright Aldo Cortesi 2010"
ns.version = "0.4"
ns.sidebar = countershape.widgets.SiblingPageIndex('/index.html')
ns.copyright = "Copyright (c) 2010 Aldo Cortesi"
this.layout = countershape.Layout("_layout.html")
this.titlePrefix = "Qtile %s - " % ns.version


pages = [
    Page("index.html", "Introduction"),
    Page("configuration.html", "Configuration"),
    Directory("configuration"),
    Page("commands.html", "API"),
    Directory("commands"),
    Page("dev.html", "Hacking Qtile"),
    Page("faq.html", "FAQ"),
    Page("admin.html", "Administrivia")
]
