from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from mobile_api.discovery.filters import DiscoveryFilterParams, apply_property_filters
from mobile_api.discovery.serializers import (
    PropertyDetailSerializer,
    PropertyListSerializer,
    UnitListSerializer,
)
from mobile_api.discovery.services import (
    build_search_suggestions,
    build_property_recommendations,
    build_stay_range_from_request,
    get_available_units_for_property,
    get_base_property_queryset,
    parse_decimal,
    parse_guest_count,
    validate_stay_range,
)
from mobile_api.pagination import MobilePageNumberPagination
from mobile_api.permissions import IsAuthenticatedOrMobileReadOnly
from settings_app.models import PropertyProfile


class DiscoveryHealthView(APIView):
    permission_classes = [IsAuthenticatedOrMobileReadOnly]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "message": "Mobile discovery API is ready.",
                "status": "ok",
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(cache_page(30), name="dispatch")
class PropertySearchSuggestionView(APIView):
    permission_classes = [IsAuthenticatedOrMobileReadOnly]

    def get(self, request, *args, **kwargs):
        q = request.query_params.get("q", "")
        try:
            limit = int(request.query_params.get("limit", 8))
        except (TypeError, ValueError):
            limit = 8
        limit = max(1, min(limit, 20))
        suggestions = build_search_suggestions(query=q, limit=limit)
        return Response({"results": suggestions}, status=status.HTTP_200_OK)


@method_decorator(cache_page(30), name="dispatch")
class PropertyListView(ListAPIView):
    serializer_class = PropertyListSerializer
    permission_classes = [IsAuthenticatedOrMobileReadOnly]
    pagination_class = MobilePageNumberPagination

    def get_queryset(self):
        stay_range = build_stay_range_from_request(self.request)
        try:
            validate_stay_range(stay_range)
        except ValueError as exc:
            raise ValidationError({"dates": str(exc)})

        guests = parse_guest_count(self.request.query_params.get("guests"))
        min_price = parse_decimal(self.request.query_params.get("min_price"))
        max_price = parse_decimal(self.request.query_params.get("max_price"))
        min_rating = parse_decimal(self.request.query_params.get("min_rating"))

        params = DiscoveryFilterParams(
            q=self.request.query_params.get("q", ""),
            country=self.request.query_params.get("country", ""),
            city=self.request.query_params.get("city", ""),
            business_type=self.request.query_params.get("business_type", ""),
            guests=guests,
            min_price=min_price,
            max_price=max_price,
            lifestyle=self.request.query_params.get("lifestyle", ""),
            amenities=self.request.query_params.get("amenities", ""),
            min_rating=min_rating,
            check_in=stay_range.check_in,
            check_out=stay_range.check_out,
        )
        queryset = get_base_property_queryset()
        return apply_property_filters(queryset, params)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        stay_range = build_stay_range_from_request(self.request)
        guests = parse_guest_count(self.request.query_params.get("guests"))

        available_map = {}
        queryset = self.filter_queryset(self.get_queryset())
        for property_obj in queryset:
            available_count = get_available_units_for_property(
                property_obj,
                check_in=stay_range.check_in,
                check_out=stay_range.check_out,
                guests=guests,
            ).count()
            available_map[property_obj.id] = available_count

        context["stay_range"] = stay_range
        context["available_unit_count_map"] = available_map
        return context


@method_decorator(cache_page(30), name="dispatch")
class FeaturedPropertyListView(ListAPIView):
    serializer_class = PropertyListSerializer
    permission_classes = [IsAuthenticatedOrMobileReadOnly]
    pagination_class = MobilePageNumberPagination

    def get_queryset(self):
        stay_range = build_stay_range_from_request(self.request)
        try:
            validate_stay_range(stay_range)
        except ValueError as exc:
            raise ValidationError({"dates": str(exc)})

        guests = parse_guest_count(self.request.query_params.get("guests"))
        queryset = get_base_property_queryset()

        if guests:
            queryset = queryset.filter(units__guest_capacity__gte=guests).distinct()

        city = self.request.query_params.get("city")
        if city:
            queryset = queryset.filter(city__iexact=city)

        country = self.request.query_params.get("country")
        if country:
            queryset = queryset.filter(country__iexact=country)

        return queryset.order_by("-created_at")[:10]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["stay_range"] = build_stay_range_from_request(self.request)
        return context


@method_decorator(cache_page(30), name="dispatch")
class RecommendedPropertyListView(ListAPIView):
    serializer_class = PropertyListSerializer
    permission_classes = [IsAuthenticatedOrMobileReadOnly]
    pagination_class = MobilePageNumberPagination

    def get_queryset(self):
        queryset = get_base_property_queryset()
        country = self.request.query_params.get("country", "")
        city = self.request.query_params.get("city", "")
        customer = None
        if getattr(self.request.user, "is_authenticated", False):
            customer = getattr(self.request.user, "mobile_customer", None)
        return build_property_recommendations(
            queryset,
            country=country,
            city=city,
            limit=10,
            customer=customer,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["stay_range"] = build_stay_range_from_request(self.request)
        return context


class PropertySearchView(PropertyListView):
    pass


class PropertyDetailView(RetrieveAPIView):
    serializer_class = PropertyDetailSerializer
    permission_classes = [IsAuthenticatedOrMobileReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return (
            PropertyProfile.objects.filter(is_active=True)
            .prefetch_related("amenities", "unit_types__amenities", "units", "experience_media")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        stay_range = build_stay_range_from_request(self.request)
        try:
            validate_stay_range(stay_range)
        except ValueError as exc:
            raise ValidationError({"dates": str(exc)})
        context["stay_range"] = stay_range
        return context


class SimilarPropertyListView(ListAPIView):
    serializer_class = PropertyListSerializer
    permission_classes = [IsAuthenticatedOrMobileReadOnly]
    pagination_class = MobilePageNumberPagination

    def get_queryset(self):
        property_obj = PropertyProfile.objects.filter(id=self.kwargs["id"], is_active=True).first()
        if not property_obj:
            return PropertyProfile.objects.none()

        base = get_base_property_queryset().filter(city__iexact=property_obj.city)
        if not base.exists():
            base = get_base_property_queryset().filter(country__iexact=property_obj.country)
        return base.exclude(id=property_obj.id).order_by("-average_rating", "-total_reviews", "-created_at")[:10]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["stay_range"] = build_stay_range_from_request(self.request)
        return context


class PropertyUnitListView(ListAPIView):
    serializer_class = UnitListSerializer
    permission_classes = [IsAuthenticatedOrMobileReadOnly]
    pagination_class = MobilePageNumberPagination

    def get_property(self):
        property_id = self.kwargs["id"]
        property_obj = PropertyProfile.objects.filter(id=property_id, is_active=True).first()
        if not property_obj:
            raise NotFound("Property not found.")
        return property_obj

    def get_queryset(self):
        property_obj = self.get_property()

        stay_range = build_stay_range_from_request(self.request)
        try:
            validate_stay_range(stay_range)
        except ValueError as exc:
            raise ValidationError({"dates": str(exc)})

        guests = parse_guest_count(self.request.query_params.get("guests"))
        return get_available_units_for_property(
            property_obj,
            check_in=stay_range.check_in,
            check_out=stay_range.check_out,
            guests=guests,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["stay_range"] = build_stay_range_from_request(self.request)
        return context
