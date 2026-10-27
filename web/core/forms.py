from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from bookings.models import Booking, BookingType, RentCycle
from guests.models import Guest, IDType
from inventory.models import Amenity, Unit, UnitType
from settings_app.models import BusinessType, PropertyProfile, DatabaseConnection
from accounts.models import OwnerProfile, StaffProfile, StaffRole
from maintenance.models import MaintenanceRequest, MaintenanceStatus
from billing.models import Invoice, Payment, PaymentMethod
from pricing.models import RatePlan, SeasonalRateRule


# =========================
# AUTH / LOGIN
# =========================
class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "slx-input",
                "placeholder": "Username or Email",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "slx-input",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        )
    )
    remember = forms.BooleanField(required=False)

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()


# =========================
# STAFF (EMPLOYEES)
# =========================
class StaffCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(choices=StaffRole.choices, widget=forms.Select(attrs={"class": "form-select"}))
    is_active = forms.BooleanField(required=False)

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()


class StaffEditForm(forms.Form):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": "form-control"}))
    role = forms.ChoiceField(choices=StaffRole.choices, widget=forms.Select(attrs={"class": "form-select"}))
    is_active = forms.BooleanField(required=False)
    reset_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))


class OwnerCreateForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": "form-control"}))
    units = forms.ModelMultipleChoiceField(queryset=Unit.objects.none(), required=False, widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "8"}))
    is_active = forms.BooleanField(required=False)

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.property_obj = property_obj
        if property_obj is not None:
            self.fields["units"].queryset = Unit.objects.filter(property_profile=property_obj, is_active=True).order_by("code")

    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip()

    def clean_units(self):
        units = self.cleaned_data.get("units")
        if not units or self.property_obj is None:
            return units

        conflict_messages = []
        for unit in units:
            conflict_owner = (
                OwnerProfile.objects.filter(property=self.property_obj, is_active=True, units=unit)
                .select_related("user")
                .first()
            )
            if conflict_owner:
                conflict_messages.append(f"{unit.code} ({conflict_owner.user.username})")

        if conflict_messages:
            raise forms.ValidationError(
                _("These units are already assigned to another owner: %(units)s")
                % {"units": ", ".join(conflict_messages)}
            )
        return units


class OwnerEditForm(forms.Form):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": "form-control"}))
    units = forms.ModelMultipleChoiceField(queryset=Unit.objects.none(), required=False, widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "8"}))
    is_active = forms.BooleanField(required=False)
    reset_password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def __init__(self, *args, property_obj=None, owner_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.property_obj = property_obj
        self.owner_instance = owner_instance
        if property_obj is not None:
            self.fields["units"].queryset = Unit.objects.filter(property_profile=property_obj, is_active=True).order_by("code")

    def clean_units(self):
        units = self.cleaned_data.get("units")
        if not units or self.property_obj is None:
            return units

        conflict_messages = []
        for unit in units:
            owner_qs = OwnerProfile.objects.filter(property=self.property_obj, is_active=True, units=unit)
            if self.owner_instance is not None:
                owner_qs = owner_qs.exclude(pk=self.owner_instance.pk)
            conflict_owner = owner_qs.select_related("user").first()
            if conflict_owner:
                conflict_messages.append(f"{unit.code} ({conflict_owner.user.username})")

        if conflict_messages:
            raise forms.ValidationError(
                _("These units are already assigned to another owner: %(units)s")
                % {"units": ", ".join(conflict_messages)}
            )
        return units


# =========================
# SETTINGS (PROPERTY)
# =========================
class PropertyProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput) or isinstance(w, forms.EmailInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.FileInput):
                w.attrs.setdefault("class", "form-control")

        if "business_type" in self.fields:
            self.fields["business_type"].label = _("Business Mode")
            self.fields["business_type"].widget = forms.RadioSelect(choices=BusinessType.choices)
        if "currency" in self.fields:
            self.fields["currency"].label = _("Currency (GCC)")

    class Meta:
        model = PropertyProfile
        fields = [
            "business_type",
            "name_en",
            "name_ar",
            "property_number",
            "phone",
            "whatsapp",
            "email",
            "address_en",
            "address_ar",
            "city",
            "country",
            "logo",
            "vat_no",
            "cr_no",
            "currency",
            "receipt_footer_en",
            "receipt_footer_ar",
            "is_active",
        ]
        labels = {
            "business_type": _("Business Mode"),
            "name_en": _("Name en"),
            "name_ar": _("Name ar"),
            "property_number": _("Property number"),
            "phone": _("Phone"),
            "whatsapp": _("Whatsapp"),
            "email": _("Email"),
            "address_en": _("Address en"),
            "address_ar": _("Address ar"),
            "city": _("City"),
            "country": _("Country"),
            "logo": _("Logo"),
            "vat_no": _("Vat no"),
            "cr_no": _("Cr no"),
            "currency": _("Currency (GCC)"),
            "receipt_footer_en": _("Receipt footer en"),
            "receipt_footer_ar": _("Receipt footer ar"),
            "is_active": _("Active"),
        }


class DatabaseConnectionForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Leave blank to keep current"}),
    )

    class Meta:
        model = DatabaseConnection
        fields = ["host", "port", "db_name", "username", "sslmode"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput) or isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")

        self.fields["sslmode"].widget = forms.Select(
            choices=[
                ("require", "require"),
                ("verify-full", "verify-full"),
                ("prefer", "prefer"),
                ("disable", "disable"),
            ],
            attrs={"class": "form-select"},
        )


class AmenityForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        if property_obj is not None:
            self.instance.property_profile = property_obj
        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")

    def clean_name_en(self):
        name = self.cleaned_data["name_en"]
        if self.instance.property_profile_id and Amenity.objects.filter(
            property_profile_id=self.instance.property_profile_id, name_en=name
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("An amenity with this English name already exists."))
        return name

    class Meta:
        model = Amenity
        fields = ["name_en", "name_ar", "is_active"]


# =========================
# INVENTORY (ROOMS/UNITS)
# =========================
class UnitTypeForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        if property_obj is not None and "amenities" in self.fields:
            self.fields["amenities"].widget = forms.CheckboxSelectMultiple()
            self.fields["amenities"].queryset = Amenity.objects.filter(
                property_profile=property_obj,
                is_active=True,
            ).order_by("name_en")

        if "name_en" in self.fields:
            self.fields["name_en"].widget = forms.Select(choices=[
                ("Standard", _("Standard")),
                ("Deluxe", _("Deluxe")),
                ("Premium", _("Premium")),
                ("Luxury", _("Luxury")),
            ])
            self.fields["name_en"].label = _("Amenity Tier")

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.CheckboxSelectMultiple):
                w.attrs.setdefault("class", "slx-amenity-options")

    class Meta:
        model = UnitType
        fields = ["name_en", "name_ar", "base_rate", "amenities", "is_active"]


class UnitForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        prop_business_type = getattr(property_obj, "business_type", None)

        # Filter unit types by active property
        try:
            if property_obj is not None and "unit_type" in self.fields:
                qs = UnitType.objects.filter(property_profile=property_obj)
                if prop_business_type:
                    qs = qs.filter(business_type=prop_business_type)
                self.fields["unit_type"].queryset = qs
        except Exception:
            pass

        if "category" in self.fields:
            if prop_business_type == BusinessType.APARTMENTS:
                self.fields["category"].label = _("Unit Type")
                self.fields["category"].choices = [
                    (Unit.UnitCategory.STUDIO_APT, _("Studio Apartment")),
                    (Unit.UnitCategory.ONE_BHK, _("1-Room / BHK")),
                    (Unit.UnitCategory.TWO_BHK, _("2-Room / BHK")),
                    (Unit.UnitCategory.THREE_BHK, _("3-Room / BHK")),
                    (Unit.UnitCategory.FOUR_BHK, _("4-Room / BHK")),
                    (Unit.UnitCategory.FIVE_BHK, _("5-Room / BHK")),
                    (Unit.UnitCategory.DUPLEX, _("Duplex / Triplex")),
                    (Unit.UnitCategory.PENTHOUSE, _("Penthouse")),
                    (Unit.UnitCategory.LOFT, _("Loft Apartment")),
                ]
            else:
                self.fields["category"].label = _("Room Type")
                self.fields["category"].choices = [
                    (Unit.UnitCategory.SINGLE, _("Single")),
                    (Unit.UnitCategory.DOUBLE, _("Double")),
                    (Unit.UnitCategory.TRIPLE, _("Triple")),
                    (Unit.UnitCategory.TWIN, _("Twin Room")),
                    (Unit.UnitCategory.KING, _("King Room")),
                    (Unit.UnitCategory.QUEEN, _("Queen Room")),
                    (Unit.UnitCategory.CONNECTING, _("Connecting / Adjoining Rooms")),
                    (Unit.UnitCategory.STUDIO, _("Studio")),
                    (Unit.UnitCategory.VILLA, _("Villa")),
                ]

        if "unit_type" in self.fields:
            self.fields["unit_type"].label = _("Amenity Tier")

        if "bed_config" in self.fields:
            self.fields["bed_config"].label = _("Bed Configuration")

        label_map = {
            "code": _("Code"),
            "floor": _("Floor"),
            "guest_capacity": _("Guest capacity"),
            "daily_price": _("Daily price"),
            "monthly_price": _("Monthly price"),
            "seasonal_price": _("Seasonal price"),
            "amenities": _("Amenities"),
            "status": _("Status"),
            "is_active": _("Is active"),
        }
        for field_name, label in label_map.items():
            if field_name in self.fields:
                self.fields[field_name].label = label

        if "amenities" in self.fields and property_obj is not None:
            self.fields["amenities"].widget = forms.CheckboxSelectMultiple()
            self.fields["amenities"].queryset = Amenity.objects.filter(property_profile=property_obj, is_active=True).order_by("name_en")

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.CheckboxSelectMultiple):
                w.attrs.setdefault("class", "slx-amenity-options")

    class Meta:
        model = Unit
        fields = [
            "unit_type",
            "category",
            "bed_config",
            "code",
            "floor",
            "guest_capacity",
            "daily_price",
            "monthly_price",
            "seasonal_price",
            "amenities",
            "status",
            "is_active",
        ]


# =========================
# GUESTS
# =========================
class GuestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Date input for ID expiry
        if "id_expiry" in self.fields:
            self.fields["id_expiry"].widget = forms.DateInput(attrs={"type": "date", "class": "form-control"})

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput) or isinstance(w, forms.EmailInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("class", "form-control")

    class Meta:
        model = Guest
        fields = [
            "full_name",
            "phone",
            "whatsapp",
            "email",
            "nationality",
            "id_type",
            "id_number",
            "id_expiry",
            "id_document",
            "address",
            "notes",
        ]
        labels = {
            "full_name": _("Full Name"),
            "phone": _("Phone"),
            "whatsapp": _("WhatsApp"),
            "email": _("Email"),
            "nationality": _("Nationality"),
            "id_type": _("ID Type"),
            "id_number": _("ID Number"),
            "id_expiry": _("ID Expiry"),
            "id_document": _("ID Document"),
            "address": _("Address"),
            "notes": _("Notes"),
        }


class GuestIdUploadForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "id_document" in self.fields:
            self.fields["id_document"].widget = forms.FileInput(attrs={"class": "form-control"})

    class Meta:
        model = Guest
        fields = ["id_document"]


# =========================
# BOOKINGS
# =========================
class BookingForm(forms.ModelForm):
    """
    Create/Edit booking (web UI).
    property_obj is used to filter available units/guests.
    """

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter units/guests by property
        try:
            if property_obj is not None:
                if "unit" in self.fields:
                    self.fields["unit"].queryset = Unit.objects.filter(
                        property_profile=property_obj,
                        unit_type__business_type=property_obj.business_type,
                    )
                if "guest" in self.fields:
                    self.fields["guest"].queryset = Guest.objects.filter(
                        property_profile=property_obj,
                        business_type=property_obj.business_type,
                    )
                if "booking_type" in self.fields:
                    if property_obj.business_type == BusinessType.APARTMENTS:
                        self.fields["booking_type"].choices = [(BookingType.APARTMENT, "Apartment")]
                        self.fields["booking_type"].initial = BookingType.APARTMENT
                    else:
                        self.fields["booking_type"].choices = [(BookingType.HOTEL, "Hotel")]
                        self.fields["booking_type"].initial = BookingType.HOTEL
        except Exception:
            pass

        # Date inputs
        for f in ["start_date", "end_date"]:
            if f in self.fields:
                self.fields[f].widget = forms.DateInput(attrs={"type": "date", "class": "form-control"})

        # UI classes
        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("class", "form-control")

    class Meta:
        model = Booking
        fields = [
            "guest",
            "unit",
            "booking_type",
            "rent_cycle",
            "status",
            "start_date",
            "end_date",
            "adults",
            "children",
            "rate",
            "discount",
            "deposit",
            "notes",
        ]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


# =========================================================
# BOOKING WIZARD (multi-step create)
# =========================================================
class BookingWizardStep1Form(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    booking_type = forms.ChoiceField(choices=BookingType.choices, widget=forms.Select(attrs={"class": "form-select"}))
    rent_cycle = forms.ChoiceField(choices=RentCycle.choices, widget=forms.Select(attrs={"class": "form-select"}))
    adults = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={"class": "form-control"}))
    children = forms.IntegerField(min_value=0, initial=0, widget=forms.NumberInput(attrs={"class": "form-control"}))

    def clean(self):
        cleaned = super().clean()
        sd = cleaned.get("start_date")
        ed = cleaned.get("end_date")
        if sd and ed and ed <= sd:
            raise forms.ValidationError("Check-out must be after check-in.")
        return cleaned


class BookingWizardStep2Form(forms.Form):
    unit = forms.ModelChoiceField(queryset=Unit.objects.none(), widget=forms.Select(attrs={"class": "form-select"}))

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        if property_obj is not None:
            self.fields["unit"].queryset = Unit.objects.filter(
                property_profile=property_obj,
                is_active=True,
                unit_type__business_type=property_obj.business_type,
            ).select_related("unit_type")


class BookingWizardGuestForm(forms.Form):
    # Choose existing OR create new
    existing_guest = forms.ModelChoiceField(queryset=Guest.objects.none(), required=False, widget=forms.Select(attrs={"class": "form-select"}))

    full_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    whatsapp = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": "form-control"}))
    nationality = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    id_type = forms.ChoiceField(choices=IDType.choices, required=False, widget=forms.Select(attrs={"class": "form-select"}))
    id_number = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}))

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        if property_obj is not None:
            self.fields["existing_guest"].queryset = Guest.objects.filter(
                property_profile=property_obj,
                business_type=property_obj.business_type,
                is_active=True,
            ).order_by("full_name")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("existing_guest"):
            return cleaned
        if not (cleaned.get("full_name") or "").strip():
            raise forms.ValidationError("Select an existing guest, or enter guest full name.")
        return cleaned


class BookingWizardPaymentForm(forms.Form):
    discount = forms.DecimalField(required=False, initial=0, min_value=0, decimal_places=3, max_digits=12,
                                 widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}))
    deposit = forms.DecimalField(required=False, initial=0, min_value=0, decimal_places=3, max_digits=12,
                                widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}))
    payment_method = forms.ChoiceField(choices=PaymentMethod.choices, widget=forms.Select(attrs={"class": "form-select"}))
    payment_amount = forms.DecimalField(required=False, initial=0, min_value=0, decimal_places=3, max_digits=12,
                                        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.001"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}))


# =========================
# MAINTENANCE
# =========================
class MaintenanceBaseForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, action=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = action

        try:
            if property_obj is not None and "unit" in self.fields:
                qs = Unit.objects.filter(property_profile=property_obj)
                if getattr(property_obj, "business_type", None):
                    qs = qs.filter(unit_type__business_type=property_obj.business_type)
                self.fields["unit"].queryset = qs
        except Exception:
            pass

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.FileInput):
                w.attrs.setdefault("class", "form-control")

        if "total_cost" in self.fields:
            self.fields["total_cost"].widget.attrs.setdefault("readonly", True)


class MaintenanceDraftForm(MaintenanceBaseForm):
    class Meta:
        model = MaintenanceRequest
        fields = [
            "unit",
            "reported_by",
            "assigned_to",
            "priority",
            "maintenance_type",
            "title",
            "description",
            "before_photo",
        ]
        labels = {
            "unit": _("Unit"),
            "reported_by": _("Reported by"),
            "assigned_to": _("Assigned to"),
            "priority": _("Priority"),
            "maintenance_type": _("Maintenance type"),
            "title": _("Title"),
            "description": _("Description"),
            "before_photo": _("Before photo"),
        }


class MaintenanceCompleteForm(MaintenanceBaseForm):
    def clean(self):
        cleaned = super().clean()
        if self.action == "finish":
            if not cleaned.get("after_photo"):
                raise forms.ValidationError("After photo is required when finishing a maintenance job.")
        return cleaned

    class Meta:
        model = MaintenanceRequest
        fields = [
            "status",
            "after_photo",
            "material_cost",
            "labor_cost",
            "total_cost",
            "completed_notes",
        ]
        labels = {
            "status": _("Status"),
            "after_photo": _("After photo"),
            "material_cost": _("Material cost"),
            "labor_cost": _("Labor cost"),
            "total_cost": _("Total cost"),
            "completed_notes": _("Completed notes"),
        }


# =========================
# BILLING (INVOICES/PAYMENTS)
# =========================
class InvoiceForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter guest/booking by property
        try:
            if property_obj is not None:
                if "guest" in self.fields:
                    self.fields["guest"].queryset = Guest.objects.filter(property_profile=property_obj)
                if "booking" in self.fields:
                    self.fields["booking"].queryset = Booking.objects.filter(property_profile=property_obj)
        except Exception:
            pass

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput) or isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("class", "form-control")

    class Meta:
        model = Invoice
        fields = [
            "booking",
            "guest",
            "invoice_no",
            "status",
            "issue_date",
            "due_date",
            "currency",
            "subtotal",
            "discount_total",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "notes",
        ]
        labels = {
            "booking": _("Booking"),
            "guest": _("Guest"),
            "invoice_no": _("Invoice no"),
            "status": _("Status"),
            "issue_date": _("Issue date"),
            "due_date": _("Due date"),
            "currency": _("Currency"),
            "subtotal": _("Subtotal"),
            "discount_total": _("Discount total"),
            "tax_total": _("Tax total"),
            "total": _("Total"),
            "amount_paid": _("Amount paid"),
            "balance_due": _("Balance due"),
            "notes": _("Notes"),
        }


class PaymentForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            if property_obj is not None and "invoice" in self.fields:
                self.fields["invoice"].queryset = Invoice.objects.filter(property_profile=property_obj)
        except Exception:
            pass

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput) or isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("class", "form-control")

    class Meta:
        model = Payment
        fields = ["invoice", "method", "direction", "amount", "reference", "paid_at", "is_void", "notes"]
        labels = {
            "invoice": _("Invoice"),
            "method": _("Method"),
            "direction": _("Direction"),
            "amount": _("Amount"),
            "reference": _("Reference"),
            "paid_at": _("Paid at"),
            "is_void": _("Is void"),
            "notes": _("Notes"),
        }


# =========================
# PRICING
# =========================
class RatePlanForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            if property_obj is not None:
                if "unit_type" in self.fields:
                    self.fields["unit_type"].queryset = UnitType.objects.filter(property_profile=property_obj)
                if "unit" in self.fields:
                    self.fields["unit"].queryset = Unit.objects.filter(property_profile=property_obj)
        except Exception:
            pass

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput) or isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")

    class Meta:
        model = RatePlan
        fields = ["name", "scope", "unit_type", "unit", "currency", "base_price_nightly", "base_price_monthly", "is_active"]


class SeasonalRateRuleForm(forms.ModelForm):
    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            if property_obj is not None and "rate_plan" in self.fields:
                self.fields["rate_plan"].queryset = RatePlan.objects.filter(property_profile=property_obj)
        except Exception:
            pass

        for f in ["date_from", "date_to"]:
            if f in self.fields:
                self.fields[f].widget = forms.DateInput(attrs={"type": "date", "class": "form-control"})

        for f in self.fields:
            w = self.fields[f].widget
            if isinstance(w, forms.TextInput) or isinstance(w, forms.NumberInput):
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")

    class Meta:
        model = SeasonalRateRule
        fields = ["rate_plan", "date_from", "date_to", "weekdays", "price_nightly", "price_monthly", "priority", "is_active"]


# =========================
# REPORTS (placeholder)
# =========================
class ReportsForm(forms.Form):
    period = forms.ChoiceField(
        choices=[
            ("custom", _("Custom")),
            ("daily", _("Daily")),
            ("weekly", _("Weekly")),
            ("monthly", _("Monthly")),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    report_type = forms.ChoiceField(
        choices=[
            ("revenue", _("Revenue")),
            ("occupancy", _("Occupancy")),
            ("maintenance", _("Maintenance")),
            ("payments", _("Payments")),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    unit = forms.ModelChoiceField(queryset=Unit.objects.none(), required=False, widget=forms.Select(attrs={"class": "form-select"}))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}))
    include_archived = forms.BooleanField(required=False)

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        if property_obj is not None:
            self.fields["unit"].queryset = Unit.objects.filter(
                property_profile=property_obj,
                is_active=True,
                unit_type__business_type=property_obj.business_type,
            ).order_by("code")
