"""The grey-label lock: no platform brand and no provider host ships.

This package is installed by integrators of different providers, and the
provider is named by the caller's `base_url` — never by us. A hostname or a
platform name that leaked into a docstring, a default argument or a
generated model would put somebody else's brand into every traceback and
every `help()` page of a provider who has nothing to do with them.

The test is a grep over the INSTALLED PACKAGE — `src/ringivo`, which is
exactly what `[tool.hatch.build.targets.wheel]` ships — rather than over the
repository. The vendored `spec/` directory is not packaged and so is not
scanned; `ringivo/_generated_types.py`, whose class names, field names and
`Literal` values are lifted from that spec, IS packaged and IS scanned,
which is the half that could regress without anybody editing a line by
hand.

Cheap and durable on purpose: it costs milliseconds, it needs no network,
and it fails on the next `scripts/generate.sh` run that pulls a branded
string out of a spec.
"""

from __future__ import annotations

import codecs
import pkgutil
import re
from pathlib import Path

import ringivo

# The names this package must never carry, kept rot13-encoded so this public
# repository does not itself spell them anywhere.
FORBIDDEN = re.compile(
    codecs.decode("gryanzvp|gryvzngvp", "rot13") + r"|ringivo\.com",
    re.IGNORECASE,
)

# Everything the wheel carries that a human or a tool can read.
SCANNED_SUFFIXES = {".py", ".pyi", ".txt", ".json", ".yaml", ".yml", ".md", ".cfg", ".typed"}


def _packaged_files() -> list[Path]:
    package = Path(ringivo.__file__).parent
    return sorted(
        path
        for path in package.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and (path.suffix in SCANNED_SUFFIXES or path.name == "py.typed")
    )


def test_no_packaged_file_names_a_platform_brand_or_a_provider_host() -> None:
    files = _packaged_files()

    # The DENOMINATOR, asserted first: "no matches" and "nothing searched"
    # must not look alike. A refactor that moved the package would otherwise
    # leave this test passing over an empty file list forever.
    #
    # It used to be a count — `> 100`, which was really a proxy for "the
    # vendored generated tree is still there". That tree is gone, and no
    # replacement count would be worth anything: this package is a dozen
    # hand-written modules, so any threshold low enough to pass is low
    # enough for a half-broken scan to pass too.
    #
    # So the denominator is CROSS-CHECKED instead of guessed, against a
    # second enumeration that shares no code with the first. `_packaged_files`
    # walks the filesystem with `rglob`; `pkgutil` asks the import system what
    # `ringivo` actually contains. A scan that quietly stopped finding files
    # would have to break both, the same way, to stay green.
    scanned = {path.name for path in files}
    modules = {f"{name}.py" for _, name, _ in pkgutil.iter_modules(ringivo.__path__)}

    # ANCHORS, so the cross-check cannot pass by finding nothing twice: two
    # empty sets satisfy `modules <= scanned` perfectly. These files are the
    # package — every one of them must be in the scan, named rather than
    # counted, and `_generated_types.py` is the machine-written half whose
    # identifiers come from the spec rather than from a person.
    anchors = {
        "__init__.py",
        "_generated_types.py",
        "async_client.py",
        "async_faxes.py",
        "client.py",
        "faxes.py",
        "models.py",
        "py.typed",
        "webhooks.py",
    }
    assert anchors <= scanned, (
        f"the scan searched {len(files)} files and missed {sorted(anchors - scanned)} — "
        "it is broken, and a clean result from it means nothing"
    )
    # And every module the import system knows about, so a file added later
    # is covered without anybody remembering to add it above.
    assert modules <= scanned, (
        f"the scan searched {len(files)} files and missed {sorted(modules - scanned)} — "
        "it is broken, and a clean result from it means nothing"
    )

    offenders = {
        str(path): sorted({match.group(0).lower() for match in FORBIDDEN.finditer(text)})
        for path in files
        if (text := path.read_text(encoding="utf-8", errors="replace")) and FORBIDDEN.search(text)
    }

    assert offenders == {}, (
        f"{len(offenders)} of {len(files)} packaged files name a forbidden brand or host: "
        f"{offenders}"
    )


def test_no_client_compiles_in_a_base_url_of_its_own() -> None:
    # The same rule from the API's side: there is no default to fall back
    # to, so a caller who forgets their provider's URL is told, not
    # silently pointed at somebody's server.
    #
    # EVERY client, found rather than listed. The file scan above catches a
    # brand or a known host wherever it appears, but a default argument
    # naming some other provider — `api.acme.example` — is forbidden by
    # this rule and by nothing else, so a client this test does not reach
    # is a client the rule does not cover.
    import inspect

    def takes_a_base_url(exported: object) -> bool:
        if not inspect.isclass(exported):
            return False
        try:
            return "base_url" in inspect.signature(exported).parameters
        except (TypeError, ValueError):
            # `inspect.signature` refuses a bare Exception subclass, and
            # most of what else this package exports is one.
            return False

    clients = {
        name: exported
        for name in ringivo.__all__
        if takes_a_base_url(exported := getattr(ringivo, name))
    }

    # The DENOMINATOR: "no client defaults its base_url" and "no client was
    # searched" must not look alike.
    assert len(clients) >= 2, f"only {sorted(clients)} was searched — the sweep is broken"

    for name, client in clients.items():
        parameter = inspect.signature(client).parameters["base_url"]
        assert parameter.default is inspect.Parameter.empty, f"{name} defaults its base_url"
