"""
Console helpers.

The reports printed by this project use box-drawing characters and emoji. A
Windows console defaults to cp1252, which cannot encode them, so the first
line printed raises UnicodeEncodeError and kills the run. Forcing UTF-8 is
preferable to stripping the output back to ASCII.

Entry-point scripts call `use_utf8_stdio()` once, before anything prints.
"""

import sys


def use_utf8_stdio():
    """Reconfigure stdout/stderr to UTF-8 so non-ASCII output cannot crash a run.

    `errors="replace"` keeps a console that still cannot render a glyph from
    raising: the character degrades to '?' instead of aborting the process.
    No-op on streams that do not support reconfiguration (e.g. when stdout has
    been replaced by a plain file object or a test capture buffer).
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
