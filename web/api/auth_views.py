from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class RecoveryContactView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        login = (request.data.get("login") or "").strip()
        if not login:
            return Response({"detail": "login is required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_model().objects.filter(
            Q(username__iexact=login) | Q(email__iexact=login)
        ).first()
        if user is None:
            return Response({"found": False}, status=status.HTTP_200_OK)

        prop = None
        try:
            staff_profile = user.staff_profile
            prop = getattr(staff_profile, "property", None)
        except ObjectDoesNotExist:
            pass

        if prop is None:
            try:
                owner_profile = user.owner_profile
                prop = getattr(owner_profile, "property", None)
            except ObjectDoesNotExist:
                pass

        if prop is None:
            return Response({"found": False}, status=status.HTTP_200_OK)

        return Response(
            {
                "found": True,
                "property_id": str(prop.id),
                "property_name": prop.name_en or "",
                "phone": prop.phone or "",
                "whatsapp": prop.whatsapp or "",
                "email": prop.email or "",
            },
            status=status.HTTP_200_OK,
        )
