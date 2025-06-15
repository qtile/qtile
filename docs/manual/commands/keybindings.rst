.. _keybinding-img:

=====================
Keybindings in images
=====================

Default configuration
=====================

.. don't delete LS_PNG and END_LS_PNG (it is used for `make genkeyimg`)
.. LS_PNG
.. image:: /_static/keybindings/mod4.png
.. image:: /_static/keybindings/mod4-shift.png
.. image:: /_static/keybindings/control-mod1.png
.. image:: /_static/keybindings/mod4-control.png
.. END_LS_PNG

Generate your own images
========================

Qtile provides a tiny helper script to generate keybindings images from a
config file. In the repository, the script is located under
``scripts/gen-keybinding-img``.

This script accepts a configuration file and an output directory. If no
argument is given, the default configuration will be used and files will be
placed in same directory where the command has been run.

::

    usage: gen-keybinding-img [-h] [-c CONFIGFILE] [-o OUTPUT_DIR]

    Qtile keybindings image generator

    optional arguments:
        -h, --help          show this help message and exit
        -c CONFIGFILE, --config CONFIGFILE
                            use specified configuration file. If no presented
                            default will be used
        -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                            set directory to export all images to
