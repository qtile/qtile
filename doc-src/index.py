import sys
sys.path.insert(0, "..")
import countershape.widgets
import countershape.layout
import countershape.grok
from countershape.doc import *
from libqtile import manager, layout, bar


def formatCommands(cmd):
    lst = []
    for i in cmd.keys():
        lst.append(
            countershape.html.rawstr(
                countershape.template.pySyntax(
                    cmd.docSig(i)
                )
            )
        )
        lst.append(
            countershape.html.rawstr(
                countershape.textish.Textish(cmd.docText(i))
            )
        )
    return countershape.html.Group(*lst)


ns.formatCommands = formatCommands
ns.commands_base = manager._BaseCommands()
ns.commands_stack = layout.StackCommands()
ns.commands_bar = bar._BarCommands()
ns.commands_textbox = bar._TextBoxCommands()
ns.commands_measurebox = bar._MeasureBoxCommands()

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
    Page("ipc.html", "Remote Commandset"),
    Page("qsh.html", "qsh - The Qtile Shell"),
    Page("faq.html", "FAQ"),
    Page("api.html", "API"),
    Page("admin.html", "Administrivia")
]
