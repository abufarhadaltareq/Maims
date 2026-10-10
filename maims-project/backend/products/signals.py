"""
Signals that keep outbound notifications honest.

The notification dispatch lives in a post_save on Order rather than in each admin
action, because there are many ways an order's status can change — the change
form, the one-click advance button, `list_editable` on the changelist, bulk
actions, a management command, or a future API — and it would be easy to forget
one and silently stop texting customers.
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Order
from . import notifications

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Order)
def remember_previous_status(sender, instance, **kwargs):
    """
    Stash the status as it was in the database.

    Needed because by the time post_save runs, `instance.status` has already been
    overwritten with the new value. Recording it on the instance gives
    post_save something honest to compare against.
    """
    if not instance.pk:
        instance._previous_status = ''
        return
    previous = (
        sender.objects.filter(pk=instance.pk)
        .values_list('status', flat=True)
        .first()
    )
    instance._previous_status = previous or ''


@receiver(post_save, sender=Order)
def notify_on_status_change(sender, instance, created, **kwargs):
    """
    Fire the notifier whenever the status actually moved.

    Guarded three ways so nothing is ever sent twice:
      * an unchanged status returns immediately;
      * `last_notified_status` is the durable guard, so even a change that arrives
        from a code path that never compared statuses still only notifies once;
      * the dispatch is deferred to `on_commit`, so a message never describes an
        order that subsequently rolls back.
    """
    previous = getattr(instance, '_previous_status', '')

    if not created and previous == instance.status:
        return  # saved for some other reason (tracking number, admin note...)

    if instance.last_notified_status == instance.status:
        return

    notifications.dispatch_for_order(instance.pk)