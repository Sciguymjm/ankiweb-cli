from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import keyring
from anki.collection import Collection
from anki.sync_pb2 import SyncAuth, SyncCollectionResponse

SERVICE = "anki-cli"


def store_password(username: str, password: str) -> None:
    keyring.set_password(SERVICE, username, password)


def get_password(username: str) -> str | None:
    return keyring.get_password(SERVICE, username)


@dataclass
class SyncResult:
    pulled: bool
    pushed: bool
    new_endpoint: str | None = None
    required_full_sync: bool = False
    server_message: str = ""


def login_and_get_hkey(
    username: str, password: str, endpoint: str
) -> tuple[str, str]:
    """Authenticate with AnkiWeb. Returns (hkey, endpoint)."""
    with tempfile.TemporaryDirectory(prefix="anki-cli-login-") as tmp:
        tmp_col_path = Path(tmp) / "throwaway.anki2"
        col = Collection(str(tmp_col_path))
        try:
            auth = col.sync_login(
                username=username, password=password, endpoint=endpoint
            )
            return auth.hkey, (auth.endpoint or endpoint)
        finally:
            col.close()


def do_sync(col: Collection, hkey: str, endpoint: str) -> SyncResult:
    auth = SyncAuth(hkey=hkey, endpoint=endpoint)
    out = col.sync_collection(auth, sync_media=True)
    required_full = out.required in (
        SyncCollectionResponse.FULL_SYNC,
        SyncCollectionResponse.FULL_DOWNLOAD,
        SyncCollectionResponse.FULL_UPLOAD,
    )
    return SyncResult(
        pulled=True,
        pushed=True,
        new_endpoint=out.new_endpoint or None,
        required_full_sync=required_full,
        server_message=out.server_message or "",
    )
