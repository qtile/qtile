# import thread
# import socket
# import Queue
# from libqtile import ipc as ipc

# Fix this apparently

# class TestServer(ipc.Server):
#     last = None

#     def __init__(self, fname):
#         ipc.Server.__init__(self, fname, self.command)

#     def command(self, data):
#         self.last = data
#         return "OK"


# def send(fname, data, q):
#     c = ipc.Client(fname)
#     while 1:
#         try:
#             d = c.send(data)
#         except socket.error:
#             continue
#         q.put(d)
#         return


# def response(s, data):
#     """
#         Returns serverData, clientData
#     """
#     q = Queue.Queue()
#     thread.start_new_thread(send, (s.fname, data, q))
#     while 1:
#         d = s.receive()
#         if s.last:
#             ret = s.last
#             break
#     s.last = None
#     return ret, q.get()


# def test_basic():
#     fname = "/tmp/testpath"
#     server = TestServer(fname)
#     assert response(server, "foo") == ("foo", "OK")

#     expected = {
#         "one": [1, 2, 3]
#     }
#     assert response(server, expected) == (expected, "OK")


# def test_big():
#     fname = "/tmp/testpath"
#     server = TestServer(fname)
#     expected = {
#         "one": [1, 2, 3] * 1024 * 5
#     }
#     assert response(server, expected) == (expected, "OK")


# def test_read_nodata():
#     fname = "/tmp/testpath"
#     s = TestServer(fname)
#     assert s.receive() == None


# def test_close():
#     fname = "/tmp/testpath"
#     s = TestServer(fname)
#     s.close()
