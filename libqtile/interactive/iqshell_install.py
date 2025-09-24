import json
import os
import sys
from tempfile import TemporaryDirectory

from jupyter_client.kernelspec import install_kernel_spec

kernel_json = {
    "argv": [
        sys.executable,
        "-m",
        "libqtile.interactive.iqshell_kernel",
        "-f",
        "{connection_file}",
    ],
    "display_name": "iqshell",
    "language": "qshell",
}


def main(argv=None):
    if argv is None:
        argv = []
    user = "--user" in argv or os.geteuid() != 0

    with TemporaryDirectory() as td:
        # IPython tempdir starts off as 700, not user readable
        os.chmod(td, 0o755)
        with open(os.path.join(td, "kernel.json"), "w") as f:
            json.dump(kernel_json, f, sort_keys=True)

        print("Installing IPython kernel spec")
        install_kernel_spec(td, "qshell", user=user, replace=True)


if __name__ == "__main__":
    main(sys.argv)
