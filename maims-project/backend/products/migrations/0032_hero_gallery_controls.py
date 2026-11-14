from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0031_product_delivery_time_and_whatsapp_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='herobannersettings',
            name='hero_eyebrow',
            field=models.CharField(
                blank=True,
                default='Curated for you',
                help_text='Short text above the hero headline. Leave blank to hide it.',
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name='herobannersettings',
            name='show_slide_navigation',
            field=models.BooleanField(
                default=True,
                help_text='Show numbered slide selectors and previous/next controls.',
                verbose_name='Show slide navigation',
            ),
        ),
        migrations.AddField(
            model_name='herobannersettings',
            name='show_progress_bar',
            field=models.BooleanField(
                default=True,
                help_text='Show the current slide number and progress bar.',
                verbose_name='Show slide progress',
            ),
        ),
    ]
