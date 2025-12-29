from libqtile.widget import canto

# Sample output of canto-remote status --tags
OUTPUT = "maintag:Canto : 10\nmaintag:Slashdot : 9\nmaintag:MintyFresh : 6\n"

# Sample tags to search for
FIRST_TAG = "maintag:Canto"
SECOND_TAG = "maintag:Slashdot"
WRONG_TAG = "user:wrong"


def test_one_tag():
    widget = canto.Canto(tags=[FIRST_TAG])

    display_text = widget.parse(OUTPUT)
    assert display_text == "maintag:Canto: 10"


def test_multiple_tags():
    widget = canto.Canto(tags=[FIRST_TAG, SECOND_TAG])

    display_text = widget.parse(OUTPUT)
    assert display_text == "maintag:Canto: 10maintag:Slashdot: 9"


def test_wrong_tags():
    widget = canto.Canto(tags=[WRONG_TAG])
    display_text = widget.parse(OUTPUT)
    assert display_text == ""


def test_all_feeds():
    widget = canto.Canto()
    display_text = widget.parse(OUTPUT)
    assert display_text == "25"
