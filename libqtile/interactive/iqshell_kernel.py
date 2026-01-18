from ipykernel.kernelbase import Kernel

from libqtile import command, ipc, sh


class QshKernel(Kernel):
    implementation = "qshell"
    implementation_version = "0.1"
    language = "no-op"
    language_version = "1.0"
    language_info = {"mimetype": "text/plain"}
    banner = "Qsh Kernel"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        socket_path = ipc.find_sockfile()
        ipc_client = ipc.Client(socket_path)
        cmd_object = command.interface.IPCCommandInterface(ipc_client)
        self.qsh = sh.QSh(cmd_object)

    def do_execute(
        self, code, silent, _store_history=True, _user_expressions=None, _allow_stdin=False
    ):
        # if no command sent, just return
        if not code.strip():
            return {
                "status": "ok",
                "execution_count": self.execution_count,
                "payload": [],
                "user_expressions": {},
            }

        if code[-1] == "?":
            return self.do_inspect(code, len(code) - 1)

        try:
            output = self.qsh.process_line(code)
        except KeyboardInterrupt:
            return {
                "status": "abort",
                "execution_count": self.execution_count,
            }

        if not silent and output:
            stream_content = {"name": "stdout", "text": output}
            self.send_response(self.iopub_socket, "stream", stream_content)

        return {
            "status": "ok",
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }

    def do_complete(self, code, cursor_pos):
        no_complete = {
            "status": "ok",
            "matches": [],
            "cursor_start": 0,
            "cursor_end": cursor_pos,
            "metadata": dict(),
        }

        if not code or code[-1] == " ":
            return no_complete

        tokens = code.split()
        if not tokens:
            return no_complete

        token = tokens[-1]
        start = cursor_pos - len(token)

        matches = self.qsh._complete(code, token)
        return {
            "status": "ok",
            "matches": sorted(matches),
            "cursor_start": start,
            "cursor_end": cursor_pos,
            "metadata": dict(),
        }


def main():
    from ipykernel.kernelapp import IPKernelApp

    IPKernelApp.launch_instance(kernel_class=QshKernel)


if __name__ == "__main__":
    main()
