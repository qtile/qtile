
import countershape.widgets
import countershape.layout
import countershape.grok
from countershape.doc import *

ns.docTitle = "Qtile"
ns.docMaintainer = "Aldo Cortesi"
ns.docMaintainerEmail = "aldo@nullcube.com"
ns.foot = "Copyright Aldo Cortesi 2008"
ns.head = readFrom("_header.html")
ns.sidebar = countershape.widgets.SiblingPageIndex('/index.html')
this.layout = countershape.layout.TwoPane("yui-t2", "doc3")
this.titlePrefix = "Qtile Manual - "

ns.qtgrok = countershape.grok.grok("../libqtile")

pages = [
    Page("index.html", "Introduction"),
    Page("configuration.html", "Configuration"),
    Page("faq.html", "FAQ"),
    Page("api.html", "API"),
    Page("admin.html", "Administrivia")
]
