from rest_framework import serializers

from mobile_api.wishlist.models import WishlistCollection, WishlistItem


class WishlistCollectionSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = WishlistCollection
        fields = [
            "id",
            "name",
            "is_public",
            "share_token",
            "items_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["share_token", "created_at", "updated_at"]


class WishlistItemSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property_profile.name_en", read_only=True)
    property_id = serializers.IntegerField(source="property_profile.id", read_only=True)
    collection_name = serializers.CharField(source="collection.name", read_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            "id",
            "property_id",
            "property_name",
            "collection",
            "collection_name",
            "price_alert_enabled",
            "target_price",
            "last_known_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
