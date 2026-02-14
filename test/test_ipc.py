import pytest

from libqtile.ipc import _IPC, IPCCommandMessage, IPCMessage, IPCReplyMessage, IPCStatus


def test_ipc_identity():
    def pack_unpack_same(msg: IPCMessage):
        serialized = _IPC.pack(msg)
        new_msg = _IPC.unpack(serialized)
        return msg == new_msg

    cmd_message = IPCCommandMessage([], "commands", (), {}, False)
    assert pack_unpack_same(cmd_message)

    cmd_message = IPCCommandMessage([("window", 1234)], "info", (), {}, False)
    assert pack_unpack_same(cmd_message)

    reply_message = IPCReplyMessage(
        IPCStatus.SUCCESS, ["some", "example", "commands", "returned"]
    )
    assert pack_unpack_same(reply_message)

    reply_message = IPCReplyMessage(IPCStatus.ERROR, "Error: Couldn't decode message")
    assert pack_unpack_same(reply_message)


def test_ipc_encoder_supports_sets():
    message = IPCReplyMessage(IPCStatus.SUCCESS, set())
    serialized = _IPC.pack(message)
    assert serialized == b'{"message_type": "reply", "content": {"status": 0, "data": []}}'


def test_ipc_throws_error_on_unsupported_field():
    class NonSerializableType: ...

    with pytest.raises(
        TypeError,
        match=("Object of type NonSerializableType is not JSON serializable"),
    ):
        _IPC.pack(IPCReplyMessage(IPCStatus.SUCCESS, NonSerializableType()))
