"""Runtime patches applied to the upstream `anki` package.

Kept in one place so the dependency on internal `anki` module names is obvious
and easy to remove if upstream changes.
"""

from __future__ import annotations


def silence_main_thread_warning() -> None:
    """Suppress anki._backend's 'blocked main thread' stack-trace spam.

    The anki library prints a stack trace to stdout whenever any backend call
    takes more than 200ms on the main thread (see anki/_backend.py). The
    warning targets GUI authors who should offload work to a worker; for a
    CLI it is unactionable noise.

    Implementation: shadow the bare `print` lookup in `anki._backend`'s module
    globals with a no-op. Python resolves bare names through module globals
    before builtins, so all `print(...)` calls inside that module become
    no-ops without affecting print elsewhere. The handful of other prints in
    `anki._backend` are deprecation warnings for APIs ankiweb-cli does not
    use, so silencing those too is acceptable collateral.
    """
    from anki import _backend

    _backend.print = lambda *args, **kwargs: None  # type: ignore[assignment]
