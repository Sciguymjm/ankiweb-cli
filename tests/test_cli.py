from click.testing import CliRunner

from ankiweb_cli.cli import main


def test_cli_runs_with_no_args() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Headless CLI" in result.output
