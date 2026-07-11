from dataclasses import dataclass
from datetime import date
from typing import Optional

from django.db.models import Avg, Q


@dataclass
class DiscoveryFilterParams:
    q: str = ""
    country: str = ""
    city: str = ""
    business_type: str = ""
    guests: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    lifestyle: str = ""
    amenities: str = ""
    min_rating: Optional[float] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None


def apply_property_filters(queryset, params: DiscoveryFilterParams):
    qs = queryset

    if params.q:
        term = params.q.strip()
        qs = qs.filter(
            Q(name_en__icontains=term)
            | Q(name_ar__icontains=term)
            | Q(city__icontains=term)
            | Q(country__icontains=term)
            | Q(address_en__icontains=term)
            | Q(address_ar__icontains=term)
            | Q(property_number__icontains=term)
        )

    if params.country:
        country_term = params.country.strip()
        qs = qs.filter(
            Q(country__iexact=country_term)
            | Q(address_en__icontains=country_term)
            | Q(address_ar__icontains=country_term)
        )

    if params.city:
        city_term = params.city.strip()
        qs = qs.filter(
            Q(city__iexact=city_term)
            | Q(address_en__icontains=city_term)
            | Q(address_ar__icontains=city_term)
        )

    if params.business_type:
        qs = qs.filter(business_type=params.business_type.strip())

    if params.guests:
        qs = qs.filter(units__guest_capacity__gte=params.guests).distinct()

    if params.min_price is not None:
        qs = qs.filter(units__daily_price__gte=params.min_price).distinct()

    if params.max_price is not None:
        qs = qs.filter(units__daily_price__lte=params.max_price).distinct()

    if params.amenities:
        amenity_terms = [part.strip() for part in params.amenities.split(",") if part.strip()]
        if amenity_terms:
            amenity_q = Q()
            for term in amenity_terms:
                amenity_q |= (
                    Q(amenities__name_en__icontains=term)
                    | Q(amenities__name_ar__icontains=term)
                    | Q(units__amenities__name_en__icontains=term)
                    | Q(units__amenities__name_ar__icontains=term)
                    | Q(unit_types__amenities__name_en__icontains=term)
                    | Q(unit_types__amenities__name_ar__icontains=term)
                )
            qs = qs.filter(amenity_q).distinct()

    if params.lifestyle:
        mode = params.lifestyle.strip().lower()
        lifestyle_terms = {
            "family": ["family", "kids", "suite", "2-room", "3-room"],
            "business": ["desk", "work", "business", "wifi", "executive"],
            "luxury": ["luxury", "premium", "spa", "concierge", "jacuzzi"],
            "beach": ["beach", "sea", "coast", "ocean"],
        }
        terms = lifestyle_terms.get(mode, [mode])
        q = Q()
        for term in terms:
            q |= (
                Q(name_en__icontains=term)
                | Q(name_ar__icontains=term)
                | Q(address_en__icontains=term)
                | Q(address_ar__icontains=term)
                | Q(amenities__name_en__icontains=term)
                | Q(amenities__name_ar__icontains=term)
                | Q(units__amenities__name_en__icontains=term)
                | Q(units__amenities__name_ar__icontains=term)
            )
        qs = qs.filter(q).distinct()

    if params.min_rating is not None:
        qs = qs.annotate(
            avg_rating=Avg(
                "reviews__rating",
                filter=Q(reviews__is_visible=True),
            )
        ).filter(avg_rating__gte=params.min_rating)

    return qs
