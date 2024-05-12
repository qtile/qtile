# Keybindings in images

## Default configuration

<!-- ```python exec="1"
import os
import sys
import subprocess
from pathlib import Path

config_dir = Path(os.environ['MKDOCS_CONFIG_DIR'])
gen_keybinding_img = config_dir / "scripts", "gen-keybinding-img"
output_dir = config_dir / "newdocs" / "_static" / "keybindings"
subprocess.run(
    [sys.executable, str(gen_keybinding_img), "-o", str(output_dir)],
    capture_output=True,
    check=False,
)
``` -->

```bash exec="1"
cd "${MKDOCS_CONFIG_DIR}/newdocs"
find _static/keybindings/* | awk '{ print length, $$0 }' | sort -n | cut -d" " -f2- | awk '{print "![image](../../../" $$1 ")"}'
```

## Generate your own images

Qtile provides a tiny helper script to generate keybindings images from a
config file. In the repository, the script is located under
`scripts/gen-keybinding-img`.

This script accepts a configuration file and an output directory. If no
argument is given, the default configuration will be used and files will be
placed in same directory where the command has been run.

```console
$ ./scripts/gen-keybinding-img
usage: gen-keybinding-img [-h] [-c CONFIGFILE] [-o OUTPUT_DIR]

Qtile keybindings image generator

optional arguments:
    -h, --help          show this help message and exit
    -c CONFIGFILE, --config CONFIGFILE
                        use specified configuration file. If no presented
                        default will be used
    -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        set directory to export all images to
```
