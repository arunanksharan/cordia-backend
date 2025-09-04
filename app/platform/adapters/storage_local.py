import os
from urllib.parse import quote
from app.platform.ports.object_storage import ObjectStoragePort
from app.core.config import settings

class LocalFilesystemStorage(ObjectStoragePort):
    def __init__(self, root: str | None = None):
        self.root = os.path.abspath(root or settings.LOCAL_STORAGE_ROOT)
        os.makedirs(self.root, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = key.strip("/").replace("..", "")
        return os.path.join(self.root, safe)

    def presign_upload(self, key: str, content_type: str, expires_seconds: int = 900) -> dict:
        # For local dev, return a pseudo-URL the frontend can PUT to your backend ingest route (not S3).
        # Since we also support direct put_bytes below, you can upload via API directly.
        return {"strategy": "direct-api", "key": key, "content_type": content_type}

    def presign_download(self, key: str, expires_seconds: int = 900) -> str:
        # For local dev, expose a static-like path; in real setups, serve via nginx or an API proxy.
        path = self._path(key)
        return f"file://{quote(path)}"

    def put_bytes(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)