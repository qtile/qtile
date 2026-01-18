from libqtile.widget import idlerpg

# Set up some fake responses
# Default widget displayes "ttl" and "online" values but can also show
# any others keys from the response so we need to include an extra field
online_response = {"player": {"ttl": 1000, "online": "1", "unused": "0"}}
offline_response = {"player": {"ttl": 10300, "online": "0"}}


# The GenPollURL widget has been tested separately so we just need to test parse
# method of this widget
def test_idlerpg():
    idler = idlerpg.IdleRPG()
    assert idler.parse(online_response) == "IdleRPG: online TTL: 0:16:40"
    assert idler.parse(offline_response) == "IdleRPG: offline TTL: 2:51:40"
