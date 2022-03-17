====================
Running Inside KDE
====================

Add the following file to the following location. This prevents kwin from starting which allows qtile to startup later on.
::
  $ cat $HOME/.config/plasma-workspace/env/wm.sh
  
  #!/bin/sh
  export KDEWM=" "
  
Now, Add the following session file
::
  $ cat /usr/share/xsessions/plasma-qtile.desktop
  
  [Desktop Entry]
  Type=XSession
  Exec=/path/to/script
  TryExec=/usr/bin/startplasma-x11
  DesktopNames=KDE
  Name=Plasma (Qtile)

Change the Exec to a new script which you can make wherever you want
::
  $ cat /path/to/script
  
  qtile start &
  startplasma-x11

Make sure that this script is executable
::
  chmod +x /path/to/script
