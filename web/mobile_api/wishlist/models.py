from django.db import models
import secrets

from core.models import TimeStampedModel
from mobile_api.auth.models import MobileCustomer
from settings_app.models import PropertyProfile


class WishlistCollection(TimeStampedModel):
    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="wishlist_collections",
    )
    name = models.CharField(max_length=120)
    is_public = models.BooleanField(default=False)
    share_token = models.CharField(max_length=32, blank=True, default="", db_index=True)

    class Meta:
        unique_together = ("customer", "name")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if self.is_public and not self.share_token:
            self.share_token = secrets.token_hex(8)
        if not self.is_public:
            self.share_token = ""
        super().save(*args, **kwargs)


class WishlistItem(TimeStampedModel):

    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    property_profile = models.ForeignKey(
        PropertyProfile,
        on_delete=models.CASCADE,
    )
    collection = models.ForeignKey(
        WishlistCollection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    price_alert_enabled = models.BooleanField(default=False)
    target_price = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    last_known_price = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "property_profile", "collection"],
                name="uniq_wishlist_item_customer_property_collection",
            ),
        ]
