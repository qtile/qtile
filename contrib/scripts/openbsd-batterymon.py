#!/usr/bin/env python
"""
    A simple laptop battery monitor for OpenBSD 4.3 or newer.

    This script updates a MeasureBox named "battery". You probably want to run
    it from crontab.
"""
import subprocess, sys
import libqtile

p = subprocess.Popen("apm -l", shell=True, stdout=subprocess.PIPE)
retcode = p.wait()
if retcode:
    print >> sys.stderr, "apm returned with error - could not update statusbar widget."

percentage = int(p.stdout.read().strip())
client = libqtile.command.Client()
client.measurebox_update("battery", percentage)


