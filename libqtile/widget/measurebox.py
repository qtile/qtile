import base

class MeasureBox(base._Widget):
    colors = ["red", "yellow", "orange", "green"]
    def __init__(self, name, width):
        """
            :name Widget name.
            :width A fixed integer width.
        """
        self.name, self.width = name, width
        self.percentage = 0

    def update(self, percentage):
        self.percentage = percentage
        self.draw()

    def draw(self):
        self.clear()
        step = 100/float(len(self.colors))
        idx = int(self.percentage/step)
        idx = idx - 1 if self.percentage == 100 else idx
        color = self.colors[idx]
        self._drawer.rectangle(
            self.offset,
            0,
            int(float(self.width)/100*self.percentage),
            self.bar.size,
            color
        )

    def cmd_update(self, percentage):
        """
            Update the percentage in a MeasureBox widget.

            :percentage An integer between 0 and 100.
        """
        if percentage > 100 or percentage < 0:
            raise command.CommandError("Percentage out of range: %s"%percentage)
        self.update(percentage)

