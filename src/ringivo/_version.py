"""The one place this package's version is written.

Its own module rather than `__init__.py` so `auth.py` can read it for the
User-Agent without importing the package root back into itself, and
`pyproject.toml`'s `[tool.hatch.version]` reads the same line the runtime
does — there is no second copy to drift.
"""

__version__ = "0.2.0"
