import libpry
from libqtile import confreader, manager, theme


class uConfig(libpry.AutoTree):
    def test_syntaxerr(self):
        libpry.raises("invalid syntax", confreader.File, "configs/syntaxerr.py")

    def test_basic(self):
        f = confreader.File("configs/basic.py")
        
    def test_theme(self):
        the = theme.Theme(
            {'bg_normal': 'BG_NORMAL_TEST',
             'fg_active': 'FG_ACTIVE_TEST',
             'fallback_test': 'FALLBACK_TEST',
             },
            specials = {'special1': {'bg_normal': 'SPECIAL_BG_NORMAL_TEST',
                                    'fg_active': 'SPECIAL_FG_ACTIVE_TEST',
                                    },
                       'special2': {'bg_normal': 'SPECIAL2_BG_NORMAL_TEST',
                                    'fg_active': 'SPECIAL2_FG_ACTIVE_TEST',
                                    }
                       }
            )
        assert the["bg_normal"] == 'BG_NORMAL_TEST'
        assert the["fg_active"] == 'FG_ACTIVE_TEST'
        
        assert the["special1_bg_normal"] == 'SPECIAL_BG_NORMAL_TEST'
        assert the["special1_fg_active"] == 'SPECIAL_FG_ACTIVE_TEST'
        assert the["special2_bg_normal"] == 'SPECIAL2_BG_NORMAL_TEST'
        assert the["special2_fg_active"] == 'SPECIAL2_FG_ACTIVE_TEST'

        assert the["foobar_fallback_test"] == 'FALLBACK_TEST'

        assert the["bg_focus"] == theme.Theme.normal['bg_focus'] #test for defaults
        
        

tests = [
    uConfig()
]
