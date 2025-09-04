from app.core.config import settings
from app.platform.ports.object_storage import ObjectStoragePort
from app.platform.adapters.storage_local import LocalFilesystemStorage
from app.platform.adapters.storage_s3 import S3Storage
from app.platform.ports.event_bus import EventBusPort
from app.platform.adapters.bus_noop import NoopEventBus
from app.platform.adapters.bus_redis import RedisEventBus
from app.platform.ports.embeddings import EmbeddingsPort
from app.platform.adapters.embeddings_hash import HashingEmbeddings

class ProviderRegistry:
    _object_storage: ObjectStoragePort | None = None
    _event_bus: EventBusPort | None = None
    _embeddings: EmbeddingsPort | None = None

    @classmethod
    def object_storage(cls) -> ObjectStoragePort:
        if cls._object_storage is None:
            if settings.OBJECT_STORAGE_PROVIDER == "s3":
                cls._object_storage = S3Storage()
            else:
                cls._object_storage = LocalFilesystemStorage(settings.LOCAL_STORAGE_ROOT)
        return cls._object_storage

    @classmethod
    def event_bus(cls) -> EventBusPort:
        if cls._event_bus is None:
            prov = (settings.EVENT_BUS_PROVIDER or "noop").lower()
            if prov == "redis":
                cls._event_bus = RedisEventBus()
            else:
                cls._event_bus = NoopEventBus()
        return cls._event_bus

    @classmethod
    def embeddings(cls) -> EmbeddingsPort:
        if cls._embeddings is None:
            prov = (settings.EMBEDDINGS_PROVIDER or "hashing").lower()
            if prov == "hashing":
                cls._embeddings = HashingEmbeddings(d=settings.EMBEDDINGS_DIM)
            else:
                # For now, only hashing is shipped. Add other adapters here.
                cls._embeddings = HashingEmbeddings(d=settings.EMBEDDINGS_DIM)
        return cls._embeddings

registry = ProviderRegistry()