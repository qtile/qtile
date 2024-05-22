# Installing on Debian or Ubuntu

To install the latest stable version of Qtile on Ubuntu (newer than 20.04) and Debian 9:

```bash
pip install xcffib
pip install qtile
```

To install the git version see [Installing From Source][installing-from-source].

NOTE: As of Ubuntu 20.04 (Focal Fossa), the package has been outdated
and removed from the Ubuntu's official package list.

## Debian 11 (bullseye)

Debian 11 comes with the necessary packages for installing Qtile. Starting 
from a minimal Debian installation, the following packages are required:

```bash
sudo apt install xserver-xorg xinit
sudo apt install libpangocairo-1.0-0
sudo apt install python3-pip python3-xcffib python3-cairocffi
```

Either Qtile can then be downloaded from the package index or the Github 
repository can be used, see [Installing From Source][installing-from-source]:

```bash
pip install qtile
```
