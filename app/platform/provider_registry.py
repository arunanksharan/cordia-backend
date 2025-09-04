from app.core.config import settings
from app.platform.ports.object_storage import ObjectStoragePort
from app.platform.adapters.storage_local import LocalFilesystemStorage
from app.platform.adapters.storage_s3 import S3Storage

class ProviderRegistry:
    _object_storage: ObjectStoragePort | None = None

    @classmethod
    def object_storage(cls) -> ObjectStoragePort:
        if cls._object_storage is None:
            if settings.OBJECT_STORAGE_PROVIDER == "s3":
                cls._object_storage = S3Storage()
            else:
                cls._object_storage = LocalFilesystemStorage(settings.LOCAL_STORAGE_ROOT)
        return cls._object_storage

registry = ProviderRegistry()