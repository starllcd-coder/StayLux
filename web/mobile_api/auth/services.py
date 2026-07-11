from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from mobile_api.auth.models import MobileCustomer

User = get_user_model()


def build_customer_token_payload(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def get_or_create_social_customer(*, provider: str, email: str, full_name: str = "", external_subject: str = ""):
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        username_base = email or f"{provider}-user"
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}-{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
            first_name=full_name,
        )

    customer, created = MobileCustomer.objects.get_or_create(
        user=user,
        defaults={
            "full_name": full_name or user.first_name or email,
            "auth_provider": provider,
            "external_subject": external_subject,
            "is_verified": True,
        },
    )

    if not created:
        updated = False
        if provider and customer.auth_provider != provider:
            customer.auth_provider = provider
            updated = True
        if external_subject and customer.external_subject != external_subject:
            customer.external_subject = external_subject
            updated = True
        if full_name and customer.full_name != full_name:
            customer.full_name = full_name
            updated = True
        if updated:
            customer.save()

    return customer