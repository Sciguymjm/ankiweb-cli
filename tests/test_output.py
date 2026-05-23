import io
import json

from anki_cli.output import emit


def test_emit_json_when_not_tty() -> None:
    buf = io.StringIO()
    emit({"foo": "bar"}, stream=buf, force_json=True)
    assert json.loads(buf.getvalue()) == {"foo": "bar"}


def test_emit_human_uses_formatter() -> None:
    buf = io.StringIO()
    emit({"foo": "bar"}, stream=buf, force_json=False, human=lambda d: f"foo is {d['foo']}")
    assert buf.getvalue().strip() == "foo is bar"
