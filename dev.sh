#!/bin/sh
set -e
set -x

echo "Creating dev environment in ./venv..."

python=python3
if [ "$#" -eq 1 ]; then
    python=$1
fi

${python} -m venv venv
. venv/bin/activate
pip install -U pip setuptools wheel

echo "Installing other required packages..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

echo ""
echo "  * Created virtualenv environment in ./venv."
echo "  * Installed all dependencies into the virtualenv."
echo "  * You can now activate the $(python3 --version) virtualenv with this command: \`. venv/bin/activate\`"
