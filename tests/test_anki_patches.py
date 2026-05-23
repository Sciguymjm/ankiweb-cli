import io
import time
from contextlib import redirect_stdout

from ankiweb_cli._anki_patches import silence_main_thread_warning

from anki import _backend


def test_main_thread_warning_silenced() -> None:
    silence_main_thread_warning()

    buf = io.StringIO()
    with redirect_stdout(buf):
        _backend.print("would normally appear")

    assert buf.getvalue() == ""


def test_silence_does_not_affect_real_print(capsys) -> None:
    # The patch shadows the name only inside anki._backend, not globally.
    silence_main_thread_warning()
    print("hello")
    assert capsys.readouterr().out == "hello\n"


def test_run_command_no_longer_prints_on_slow_call(monkeypatch) -> None:
    # Simulate the anki._backend._run_command code path by exercising the
    # exact branch that prints the stack trace.
    silence_main_thread_warning()

    buf = io.StringIO()
    with redirect_stdout(buf):
        # Mimic _run_command's diagnostic block directly:
        elapsed = 1.5  # > 0.2s
        if elapsed > 0.2:
            _backend.print(f"blocked main thread for {int(elapsed * 1000)}ms:")

    assert buf.getvalue() == ""
    # Sanity: time module still works (no global breakage)
    time.time()
