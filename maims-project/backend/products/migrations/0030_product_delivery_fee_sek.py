from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0029_hero_video_and_delivery_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='delivery_fee_sek',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Leave blank to use the standard 85 SEK delivery fee. Set to 0 for free delivery.',
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
