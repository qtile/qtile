import libqtile.backend


def identify_output(opts) -> None:
    kore = libqtile.backend.get_core("x11")
    output_info = kore.get_output_info()
    kore.finalize()

    print("Output Information:")

    for i, info in enumerate(output_info):
        name = info.name or "Unknown"
        serial = info.serial or "N/A"

        print(f"Output {i}:")
        print(f"  Name: {name}")
        print(f"  Serial Number: {serial}")
        print(f"  Position: ({info.rect.x}, {info.rect.y})")
        print(f"  Resolution: {info.rect.width}x{info.rect.height}")
        print()


def add_subcommand(subparsers, parents):
    parser = subparsers.add_parser(
        "x11-identify-output",
        parents=parents,
        help="Print output names, positions, and serial numbers (X11 only).",
    )
    parser.set_defaults(func=identify_output)
