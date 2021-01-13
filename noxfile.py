import os

import nox

NOXENV = os.environ.get('NOXENV')
PYTHONS = NOXENV or [
    '3.7',
    'pypy3.7',
    '3.8',
    '3.9',
]
PYTHON = NOXENV or PYTHONS[-1]


def setup(session):
    session.install('-r', 'requirements/xcffib.txt')


def cffi_build(session):
    session.run(
        '/bin/sh',
        'scripts/ffibuild',
        success_codes=[0, 1],
        external=True,
        silent=True,
    )


@nox.session(python=PYTHON)
def test(session):
    setup(session)
    session.install('-r', 'requirements/test.txt')
    cffi_build(session)
    session.run(
        'pytest',
        '-Wall',
        '--cov',
        'libqtile',
        '--cov-report',
        'term-missing',
    )


@nox.session(python=PYTHON)
def static(session):
    setup(session)
    session.install('-r', 'requirements/static.txt')
    cffi_build(session)
    session.run('mypy', '-p', 'libqtile')


@nox.session(python=PYTHON)
def lint(session):
    setup(session)
    session.install('-r', 'requirements/lint.txt')
    session.run(
        'flake8',
        'libqtile',
        'noxfile.py',
        'test',
        'setup.py',
    )


@nox.session(python=PYTHON)
def format(session):
    session.install('-r', 'requirements/format.txt')
    session.run('isort', 'libqtile', 'bin', 'test')


@nox.session(python=PYTHON)
def docs(session):
    session.install('-r', 'requirements/docs.txt')
    session.run('python3', 'setup.py', 'build_sphinx', '-W')


@nox.session(python=PYTHON)
def package(session):
    setup(session)
    session.install('-r', 'requirements/package.txt')
    cffi_build(session)
    session.run('check-manifest')
    session.run('python3', 'setup.py', 'check', '-m', '-s')
    session.run('python3', 'setup.py', 'sdist')
    session.run('twine', 'check', 'dist/*')
