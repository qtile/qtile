import asyncio

from libqtile import config, layout
from libqtile.backend.macos.core import Core
from libqtile.confreader import Config
from libqtile.core.manager import Qtile


class TestConfig(Config):
    groups = [config.Group("a")]
    layouts = [layout.stack.Stack(num_stacks=1)]
    keys = []
    mouse = []
    screens = [config.Screen()]


async def run_debug():
    print("Creating core...")
    kore = Core()
    print("Core created.")

    print("Instantiating Qtile...")
    q = Qtile(kore, TestConfig(), socket_path="/tmp/qtile-macos-test.sock")
    print("Qtile instantiated.")

    print("Starting loop for 10 seconds...")
    # We use q.async_loop() directly to have more control
    loop = asyncio.get_running_loop()
    q._eventloop = loop
    q.core.qtile = q

    # Simulate parts of async_loop
    q.load_config(initial=True)
    q.core.setup_listener()

    print(f"Initially managed windows: {list(q.windows_map.keys())}")

    try:
        await asyncio.wait_for(q._stopped_event.wait(), timeout=10)
    except TimeoutError:
        print("Timeout reached, stopping...")
    finally:
        q.stop()
        q.core.finalize()
    print("Done.")


if __name__ == "__main__":
    try:
        asyncio.run(run_debug())
    except KeyboardInterrupt:
        pass
