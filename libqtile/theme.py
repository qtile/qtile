
'''
bg_norm, focus, urgent
fg_norm, focus, urgent
group_**

'''

class Theme(object):
    normal = {
        'fg_normal': '#ffffff',
        'fg_focus': '#ff0000',
        'fg_active': '#990000',
        'bg_normal': '#000000',
        'bg_focus': '#ffffff',
        'bg_active': '#888888',
        'border': '#0000ff',
        'font': None,
        }
    specials = {}
    def __init__(self, values, specials=None):
        for key, value in values.items():
            self.normal[key] = value
        if specials:
            for key, value in specials.items():
                self.specials[key] = value

    def __getitem__(self, key):
        if key in self.normal:
            return self.normal[key]
        else:
            parts = key.split("_")
            special = parts[0]
            key = '_'.join(parts[1:])
            if special in self.specials and key in self.specials[special]:
                return self.specials[special][key]
            elif key in self.normal:
                return self.normal[key]
            else:
                return None
    
