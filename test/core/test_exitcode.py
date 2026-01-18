def test_exitcode_default(manager):
    manager.c.shutdown()
    manager.proc.join()
    assert manager.proc.exitcode == 0


def test_exitcode_explicit(manager):
    code = 23
    manager.c.shutdown(code)
    manager.proc.join()
    assert manager.proc.exitcode == code
