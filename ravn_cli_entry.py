"""PyInstaller entry point for the packaged RAVN command-line executable.

`ravn_app/cli.py` already guards itself with `if __name__ == "__main__": cli()`, but
PyInstaller needs a dedicated top-level script it can freeze: pointing it straight at
`ravn_app/cli.py` would execute that module as `__main__`, so the very same code would
also be imported a second time under its real name `ravn_app.cli` by anything that
imports it -- giving two copies of the Click group and its module-level state.

This wrapper keeps the packaged CLI importing `ravn_app.cli` exactly once, the same way
`ravn.py` is the entry point for the GUI build.
"""

from ravn_app.cli import cli


if __name__ == "__main__":
    cli()
