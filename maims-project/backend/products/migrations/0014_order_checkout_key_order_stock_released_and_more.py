from django.db import migrations, models


def _dedupe_slugs(apps, schema_editor):
    """
    Make slugs unique before the unique index is created.

    The public API resolves a product with ``Product.objects.get(slug=...)``, so a
    duplicate slug turns a product page into a 500 rather than serving the wrong
    item. Enforcing uniqueness therefore needs a database index — but adding that
    index fails outright on any deployed database that already holds duplicates.
    Rather than let the deployment crash, rename the later duplicates and keep
    every row; only the suffixed slugs change, and only when a collision exists.
    """
    for model_name in ('category', 'collection', 'product'):
        model = apps.get_model('products', model_name)
        seen = set()
        duplicates = []
        # Order by slug so the suffixing is deterministic across databases.
        for pk, slug in model.objects.order_by('slug', 'pk').values_list('pk', 'slug'):
            if slug in seen:
                duplicates.append((pk, slug))
            else:
                seen.add(slug)

        for pk, slug in duplicates:
            candidate = f'{slug}-{pk}'
            # A pre-existing row could already hold the suffixed form.
            suffix = 2
            while candidate in seen:
                candidate = f'{slug}-{pk}-{suffix}'
                suffix += 1
            seen.add(candidate)
            model.objects.filter(pk=pk).update(slug=candidate)


def _noop_reverse(apps, schema_editor):
    """Renaming duplicates cannot be undone: the original slugs are unrecoverable."""


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0013_alter_collection_options_alter_order_options_and_more'),
    ]

    operations = [
        # Must run BEFORE the AlterField operations that add the unique index.
        migrations.RunPython(_dedupe_slugs, _noop_reverse),

        migrations.AddField(
            model_name='order',
            name='checkout_key',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='order',
            name='stock_released',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(unique=True),
        ),
        migrations.AlterField(
            model_name='collection',
            name='slug',
            field=models.SlugField(unique=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(unique=True),
        ),
    ]
