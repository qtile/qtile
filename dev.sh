#!/bin/sh
set -e
set -x

echo "Creating dev environment in ./venv..."

python3.7 -m venv venv
. venv/bin/activate
pip3.7 install -U pip setuptools

# https://github.com/qtile/qtile/issues/994
echo "Installing xcffib then cairocffi..."
pip3.7 install --no-cache-dir 'xcffib >= 0.5.0' && pip3.7 install --no-cache-dir 'cairocffi >= 0.9.0'

pip3.7 install -r requirements.txt
pip3.7 install -r requirements-dev.txt

echo ""
echo "  * Created virtualenv environment in ./venv."
echo "  * Installed all dependencies into the virtualenv."
echo "  * You can now activate the $(python3 --version) virtualenv with this command: \`. venv/bin/activate\`"
