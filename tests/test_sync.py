from anki_cli import sync


def test_keyring_store_and_get(monkeypatch) -> None:
    store: dict[tuple[str, str], str] = {}

    def fake_set(service: str, user: str, pw: str) -> None:
        store[(service, user)] = pw

    def fake_get(service: str, user: str) -> str | None:
        return store.get((service, user))

    monkeypatch.setattr(sync.keyring, "set_password", fake_set)
    monkeypatch.setattr(sync.keyring, "get_password", fake_get)

    sync.store_password("u@example.com", "secret")
    assert sync.get_password("u@example.com") == "secret"
