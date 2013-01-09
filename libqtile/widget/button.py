from .. import bar, manager
import base


def defaultfunc():
	return

class _Button(base._TextBox):
	"""
	Base class for button widgets

	Essentially text boxes with a click function

	Looking to add an image representation before the text,
	possibly requiring changing the inherited class to base._Widget
	and needing to rebuild a lot of the functionality
	"""
	defaults = manager.Defaults(
        ("font", "Arial", "Clock font"),
        ("fontsize", None, "Clock pixel size. Calculated if None."),
        ("padding", None, "Clock padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )
	def __init__(self, text=" ", width=bar.CALCULATED, function=defaultfunc, **config):
		base._TextBox.__init__(self, text, width, **config)
		self.function = function
	def click(self, x, y, button):
		self.function(x, y, button)
class SampleButton(_Button):
	def __init__(self):
		_Button.__init__(self, text="Click Here", function=self.function)
	def function(self, x, y, button):
		if self.background=="000fff":
			self.background="cc33cc"
		else:
			self.background="000fff"
		self.draw()
class ExitButton(_Button):
	def __init__(self):
		_Button.__init__(self, text="Logout", function=self.function)
	def function(self, x, y, button):
		self.qtile.cmd_shutdown()
