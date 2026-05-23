from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import IO, Any


def emit(
    data: Any,
    *,
    stream: IO[str] | None = None,
    force_json: bool | None = None,
    human: Callable[[Any], str] | None = None,
) -> None:
    out = stream if stream is not None else sys.stdout
    use_json = force_json if force_json is not None else not out.isatty()
    if use_json or human is None:
        json.dump(data, out, indent=2, ensure_ascii=False, default=str)
        out.write("\n")
    else:
        text = human(data)
        out.write(text)
        if not text.endswith("\n"):
            out.write("\n")
