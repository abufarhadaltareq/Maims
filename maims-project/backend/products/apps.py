from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = 'products'

    def ready(self):
        # Registers the order-status signal that drives customer notifications,
        # admin alerts and Facebook success stories. Without this import the
        # post_save receiver never connects and no message is ever sent.
        from . import signals  # noqa: F401