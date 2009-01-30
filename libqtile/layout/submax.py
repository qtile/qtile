from base import SubLayout, Rect
from sublayouts import VerticalStack

class SubMax(VerticalStack): #just a vertical stack with one item
    def filter_windows(self, windows):
        if self.clientStack.focus_history:
            current = self.clientStack.focus_history[0]
        else:
            current = self.clientStack.group.currentWindow
        if current in windows:
            return [current,]
        else:
            #it must have been taken by floating or something
            if self.clientStack.focus_history:
                for c in self.clientStack.focus_history:
                    if c in windows:
                        return [c,]
        #give up, we'll arrange nothing
        return []

    def request_rectangle(self, r, windows):
        # take what you can, give nothing back
        return (r, Rect(0,0,0,0))
