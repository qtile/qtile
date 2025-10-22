try:
    # Shorten the import for this because it will be used in configs
    from libqtile.backend.wayland.inputs import InputConfig  # noqa: F401
except ModuleNotFoundError:
    print("InputConfig couldn't be imported from libqtile.backend.wayland")
    print("If this happened during setup.py installation, ignore this message.")
    print("Otherwise, make sure to run ./scripts/ffibuild.")
