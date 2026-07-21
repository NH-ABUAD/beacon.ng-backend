from django.conf import settings
from django.core.files.storage import FileSystemStorage

try:
    from cloudinary_storage.storage import MediaCloudinaryStorage
except ImportError:  # pragma: no cover
    MediaCloudinaryStorage = None


class ConfiguredStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        if MediaCloudinaryStorage is not None and getattr(settings, 'CLOUDINARY_URL', None):
            self._backend = MediaCloudinaryStorage()
        else:
            super().__init__(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)

    def _open(self, name, mode='rb'):
        if hasattr(self, '_backend'):
            return self._backend._open(name, mode)
        return super()._open(name, mode)

    def _save(self, name, content):
        if hasattr(self, '_backend'):
            return self._backend._save(name, content)
        return super()._save(name, content)

    def delete(self, name):
        if hasattr(self, '_backend'):
            return self._backend.delete(name)
        return super().delete(name)

    def exists(self, name):
        if hasattr(self, '_backend'):
            return self._backend.exists(name)
        return super().exists(name)
