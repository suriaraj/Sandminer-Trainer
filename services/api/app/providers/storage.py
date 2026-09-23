from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredObject:
    key: str
    content_type: str
    size: int


class StorageProvider:
    def create_upload(self, *, category: str, content_type: str, size: int) -> StoredObject:
        raise NotImplementedError

    def signed_download_url(self, key: str, expires_seconds: int = 300) -> str:
        raise NotImplementedError
