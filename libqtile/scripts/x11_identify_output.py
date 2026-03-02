import os


def identify_output(opts) -> None:
    from libqtile.backend.x11.xcbq import Connection

    conn = Connection(os.environ.get("DISPLAY"))

    print("Output Information:")

    try:
        for i, info in enumerate(conn.pseudoscreens):
            port = info.port or "Unknown"
            make = info.make or "Unknown"
            model = info.model or "Unknown"
            serial = info.serial or "Unknown"

            print(f"Output {i}:")
            print(f"  Port: {port}")
            print(f"  Make: {make}")
            print(f"  Model: {model}")
            print(f"  Serial Number: {serial}")
            print(f"  Position: ({info.rect.x}, {info.rect.y})")
            print(f"  Resolution: {info.rect.width}x{info.rect.height}")
            print()
    finally:
        conn.finalize()


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "x11-identify-output",
        parents=parents,
        help="Print output names, positions, and serial numbers (X11 only).",
    )
    parser.set_defaults(func=identify_output)
