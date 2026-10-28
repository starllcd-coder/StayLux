from rest_framework import viewsets
from core.security import get_user_property_profile_id
from settings_app.models import PropertyProfile
from rest_framework.exceptions import PermissionDenied


class PropertyScopedModelViewSet(viewsets.ModelViewSet):
    """
    Multi-branch rules:
    - Superuser: can see all
    - Normal staff: only see their StaffProfile.property_profile
    - You can still filter with ?property_profile=ID, but it must match staff property
    """

    property_field_name = "property_profile"  # default FK name

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user.is_superuser:
            return
        staff = getattr(request.user, "staff_profile", None)
        if not request.user.is_authenticated or not request.user.is_active or not staff or not staff.is_active:
            raise PermissionDenied("An active property staff profile is required.")

    def _resolve_property_id(self):
        req_prop = self.request.query_params.get("property_profile")
        if req_prop:
            try:
                return int(req_prop)
            except ValueError:
                return None
        return self._user_prop_id()

    def get_property_profile(self):
        prop_id = self._resolve_property_id()
        if not prop_id:
            return None
        return PropertyProfile.objects.filter(id=prop_id).first()

    def _user_prop_id(self):
        if self.request.user.is_superuser:
            return None
        return get_user_property_profile_id(self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        user_prop_id = self._user_prop_id()
        if user_prop_id is None:
            return qs

        # If request includes property_profile, enforce it matches
        req_prop = self.request.query_params.get("property_profile")
        if req_prop:
            try:
                req_prop_int = int(req_prop)
            except ValueError:
                return qs.none()
            if req_prop_int != user_prop_id:
                return qs.none()
            return qs.filter(**{f"{self.property_field_name}_id": req_prop_int})

        return qs.filter(**{f"{self.property_field_name}_id": user_prop_id})

    def perform_create(self, serializer):
        """
        Auto-set property_profile from logged-in staff if not provided.
        Superuser can pass property_profile manually.
        """
        if self.request.user.is_superuser:
            return serializer.save()

        user_prop_id = self._user_prop_id()
        if user_prop_id is None:
            return serializer.save()

        # If serializer has the field, set it
        if self.property_field_name in serializer.fields:
            return serializer.save(**{self.property_field_name + "_id": user_prop_id})

        return serializer.save()
