import manager

class Config:
    groups = ["a", "b", "c", "d"]
    layouts = [manager.Max]
    keys = [
        manager.Key(["control"], "k", "focusnext"),
        manager.Key(["control"], "j", "focusprevious"),
    ]
    commands = []
    screens = []
