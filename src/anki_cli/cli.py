import click


@click.group()
@click.version_option()
def main() -> None:
    """Headless CLI for AnkiWeb."""


if __name__ == "__main__":
    main()
