from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0030_product_delivery_fee_sek'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='delivery_time',
            field=models.CharField(
                default='20-25 days',
                help_text='Estimated delivery time shown at checkout and in order notifications.',
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_template_name',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Exact name of the approved Meta template with one text placeholder in its body.',
                max_length=128,
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='whatsapp_template_language',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Language code configured for the approved WhatsApp template, e.g. en.',
                max_length=16,
            ),
        ),
    ]
