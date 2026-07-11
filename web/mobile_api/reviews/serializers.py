from rest_framework import serializers

from mobile_api.reviews.models import PropertyReview


class PropertyReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = PropertyReview
        fields = [
            "id",
            "customer",
            "customer_name",
            "property_profile",
            "rating",
            "title",
            "comment",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "created_at",
        ]


class PropertyReviewCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PropertyReview
        fields = [
            "property_profile",
            "rating",
            "title",
            "comment",
        ]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value