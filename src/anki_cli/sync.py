from __future__ import annotations

import shutil
import tempfile
from datetime import datetime
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


def do_full_sync(
    col_path: Path,
    backups_dir: Path,
    *,
    username: str,
    password: str,
    endpoint: str,
    upload: bool,
) -> dict[str, object]:
    """Force a full upload or download. Replaces local collection on download.

    Logs in on the real Collection (no throwaway), runs sync_collection so the
    backend captures server state, then close_for_full_sync, then
    full_upload_or_download.
    """
    backups_dir.mkdir(parents=True, exist_ok=True)
    if col_path.exists():
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        direction = "upload" if upload else "download"
        shutil.copy2(col_path, backups_dir / f"collection-{ts}-full-{direction}.anki2")
    col_path.parent.mkdir(parents=True, exist_ok=True)
    col = Collection(str(col_path))
    try:
        auth = col.sync_login(username=username, password=password, endpoint=endpoint)
        out = col.sync_collection(auth, sync_media=False)
        server_usn = out.server_media_usn
        # sync_collection performs a 308-redirect from sync.ankiweb.net to a
        # numbered shard (e.g. sync15.ankiweb.net) and returns the resolved URL
        # in new_endpoint.  full_upload_or_download creates a fresh HTTP client
        # from auth.endpoint, so we must point auth at the shard before calling
        # it; otherwise the download request lands on the load-balancer which
        # returns a 303 with no body/headers, causing "missing original size".
        resolved_endpoint = out.new_endpoint or endpoint
        auth_for_full = SyncAuth(hkey=auth.hkey, endpoint=resolved_endpoint)
        col.close_for_full_sync()
        col.full_upload_or_download(auth=auth_for_full, server_usn=server_usn, upload=upload)
    finally:
        try:
            col.close()
        except Exception:
            pass
    return {
        "ok": True,
        "direction": "upload" if upload else "download",
        "endpoint": resolved_endpoint,
    }
