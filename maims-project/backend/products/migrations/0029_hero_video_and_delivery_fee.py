from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0028_heroslide_badge_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='heroslide',
            name='media_type',
            field=models.CharField(
                choices=[('image', 'Image'), ('video', 'Video')],
                default='image',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='heroslide',
            name='video',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='uploads/hero/videos/',
            ),
        ),
        migrations.AddField(
            model_name='heroslide',
            name='external_video_url',
            field=models.URLField(
                blank=True,
                help_text='Optional https:// video URL. Uploaded video takes precedence.',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
            ),
        ),
    ]
