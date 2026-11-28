from django.db import migrations, models


OLD_COPY = {
    'tagline': 'Premium Fashion',
    'footer_about': 'Curated premium fashion, delivered worldwide.',
    'footer_bottom_note': 'Premium fashion, delivered worldwide',
}
NEW_COPY = {
    'tagline': 'Traditional & Modern South Asian Wear',
    'footer_about': (
        'Traditional and modern South Asian wear, blending cultural style '
        'with contemporary fashion.'
    ),
    'footer_bottom_note': 'Traditional & Modern South Asian Wear',
}


def update_default_brand_copy(apps, schema_editor, source, target):
    SiteSettings = apps.get_model('products', 'SiteSettings')
    database = schema_editor.connection.alias
    for field, old_value in source.items():
        SiteSettings.objects.using(database).filter(**{field: old_value}).update(
            **{field: target[field]}
        )


def forwards(apps, schema_editor):
    update_default_brand_copy(apps, schema_editor, OLD_COPY, NEW_COPY)


def backwards(apps, schema_editor):
    update_default_brand_copy(apps, schema_editor, NEW_COPY, OLD_COPY)


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0036_video_media_storage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='tagline',
            field=models.CharField(
                blank=True,
                default='Traditional & Modern South Asian Wear',
                help_text='Short line under the logo, e.g. Traditional & Modern South Asian Wear.',
                max_length=120,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='footer_about',
            field=models.CharField(
                blank=True,
                default=(
                    'Traditional and modern South Asian wear, blending cultural style '
                    'with contemporary fashion.'
                ),
                help_text='One-line shop description in the footer.',
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='footer_bottom_note',
            field=models.CharField(
                blank=True,
                default='Traditional & Modern South Asian Wear',
                help_text='Small line at the very bottom of the footer.',
                max_length=255,
                null=True,
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
