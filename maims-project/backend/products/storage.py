from django.conf import settings
from os.path import splitext

if settings.DEBUG:
    from django.core.files.storage import FileSystemStorage

    class VideoMediaStorage(FileSystemStorage):
        pass

    class ProductMediaStorage(FileSystemStorage):
        pass
else:
    from cloudinary_storage.storage import MediaCloudinaryStorage

    class VideoMediaStorage(MediaCloudinaryStorage):
        RESOURCE_TYPE = 'video'

    class ProductMediaStorage(MediaCloudinaryStorage):
        def _get_resource_type(self, name):
            return 'video' if splitext(name)[1].lower() in {
                '.mp4', '.webm', '.ogv', '.ogg',
            } else 'image'
