from django.db.models import Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from mobile_api.permissions import IsMobileCustomer
from mobile_api.wishlist.models import WishlistCollection, WishlistItem
from mobile_api.wishlist.serializers import WishlistCollectionSerializer, WishlistItemSerializer


class WishlistListView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request):

        items = WishlistItem.objects.filter(
            customer=request.user.mobile_customer
        ).select_related("property_profile", "collection")

        return Response(WishlistItemSerializer(items, many=True).data)


class WishlistToggleView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request):

        property_id = request.data.get("property_id")
        collection_id = request.data.get("collection_id")

        item = WishlistItem.objects.filter(
            customer=request.user.mobile_customer,
            property_profile_id=property_id,
            collection_id=collection_id,
        ).first()

        if item:
            item.delete()
            return Response({"removed": True})

        created = WishlistItem.objects.create(
            customer=request.user.mobile_customer,
            property_profile_id=property_id,
            collection_id=collection_id,
        )

        return Response(
            {"added": True, "item": WishlistItemSerializer(created).data},
            status=status.HTTP_201_CREATED,
        )


class WishlistCollectionListCreateView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request):
        qs = WishlistCollection.objects.filter(customer=request.user.mobile_customer).annotate(items_count=Count("items"))
        return Response(WishlistCollectionSerializer(qs, many=True).data)

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": "Collection name is required."}, status=status.HTTP_400_BAD_REQUEST)
        is_public = bool(request.data.get("is_public"))
        obj, _ = WishlistCollection.objects.get_or_create(
            customer=request.user.mobile_customer,
            name=name,
            defaults={"is_public": is_public},
        )
        if obj.is_public != is_public:
            obj.is_public = is_public
            obj.save(update_fields=["is_public", "share_token", "updated_at"])
        return Response(WishlistCollectionSerializer(obj).data, status=status.HTTP_201_CREATED)


class WishlistCollectionShareView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, id):
        collection = WishlistCollection.objects.filter(
            id=id,
            customer=request.user.mobile_customer,
        ).first()
        if not collection:
            return Response({"detail": "Collection not found."}, status=status.HTTP_404_NOT_FOUND)
        collection.is_public = True
        collection.save(update_fields=["is_public", "share_token", "updated_at"])
        share_url = f"/api/mobile/wishlist/shared/{collection.share_token}/"
        return Response({"share_url": share_url, "token": collection.share_token}, status=status.HTTP_200_OK)


class WishlistSharedCollectionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        collection = WishlistCollection.objects.filter(share_token=token, is_public=True).first()
        if not collection:
            return Response({"detail": "Collection not found."}, status=status.HTTP_404_NOT_FOUND)
        items = collection.items.select_related("property_profile", "collection")
        return Response(
            {
                "collection": WishlistCollectionSerializer(collection).data,
                "items": WishlistItemSerializer(items, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class WishlistPriceAlertView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, id):
        item = WishlistItem.objects.filter(id=id, customer=request.user.mobile_customer).first()
        if not item:
            return Response({"detail": "Wishlist item not found."}, status=status.HTTP_404_NOT_FOUND)

        enabled = bool(request.data.get("enabled", True))
        target_price = request.data.get("target_price")
        item.price_alert_enabled = enabled
        item.target_price = target_price if target_price not in ("", None) else None
        if item.last_known_price is None:
            item.last_known_price = item.property_profile.units.filter(is_active=True).order_by("daily_price").values_list("daily_price", flat=True).first()
        item.save(update_fields=["price_alert_enabled", "target_price", "last_known_price", "updated_at"])
        return Response(WishlistItemSerializer(item).data, status=status.HTTP_200_OK)
