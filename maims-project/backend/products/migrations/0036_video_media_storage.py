import products.storage
import os
from urllib.parse import urlparse

from django.db import migrations, models


VIDEO_EXTENSIONS = {'.mp4', '.webm', '.ogv', '.ogg'}


def detect_existing_videos(apps, schema_editor):
    HeroSlide = apps.get_model('products', 'HeroSlide')
    ProductMedia = apps.get_model('products', 'ProductMedia')
    database = schema_editor.connection.alias

    for slide in HeroSlide.objects.using(database).iterator():
        video_name = slide.video or slide.external_video_url or ''
        if slide.video or os.path.splitext(urlparse(video_name).path)[1].lower() in VIDEO_EXTENSIONS:
            HeroSlide.objects.using(database).filter(pk=slide.pk).update(media_type='video')

    for media in ProductMedia.objects.using(database).iterator():
        media_name = media.file or media.external_url or ''
        if os.path.splitext(urlparse(media_name).path)[1].lower() in VIDEO_EXTENSIONS:
            ProductMedia.objects.using(database).filter(pk=media.pk).update(media_type='video')


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0035_product_retention_settings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='heroslide',
            name='video',
            field=models.FileField(
                blank=True,
                help_text='Upload an MP4, WebM, Ogg, or OGV video. Uploading a video selects Video automatically.',
                null=True,
                storage=products.storage.VideoMediaStorage(),
                upload_to='uploads/hero/videos/',
            ),
        ),
        migrations.AlterField(
            model_name='heroslide',
            name='external_video_url',
            field=models.URLField(
                blank=True,
                help_text='Optional direct HTTPS link to an MP4, WebM, Ogg, or OGV video file. '
                          'YouTube/Vimeo page links are not playable here.',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='productmedia',
            name='file',
            field=models.FileField(
                blank=True,
                help_text='Upload an image or MP4/WebM/Ogg/OGV video. Video uploads are detected automatically.',
                null=True,
                storage=products.storage.ProductMediaStorage(),
                upload_to='uploads/',
            ),
        ),
        migrations.AlterField(
            model_name='productmedia',
            name='external_url',
            field=models.URLField(
                blank=True,
                help_text='For video, use a direct HTTPS link to an MP4/WebM/Ogg/OGV file (not a YouTube/Vimeo page).',
                null=True,
            ),
        ),
        migrations.RunPython(detect_existing_videos, migrations.RunPython.noop),
    ]
