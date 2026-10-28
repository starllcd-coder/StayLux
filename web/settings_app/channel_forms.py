from django import forms
from django.utils.translation import gettext_lazy as _
from inventory.models import Unit
from .models import ChannelIntegration
from .channel_security import credential_storage_ready


class ChannelIntegrationForm(forms.ModelForm):
    access_token = forms.CharField(required=False, max_length=4096, label=_("API token / API key"), widget=forms.PasswordInput)
    client_id = forms.CharField(required=False, max_length=255, label=_("OAuth client ID"), widget=forms.PasswordInput)
    client_secret = forms.CharField(required=False, max_length=4096, label=_("OAuth client secret"), widget=forms.PasswordInput)
    api_username = forms.CharField(required=False, max_length=255, label=_("API machine username"), widget=forms.PasswordInput)
    api_password = forms.CharField(required=False, max_length=4096, label=_("API machine password"), widget=forms.PasswordInput)
    clear_credentials = forms.BooleanField(required=False, label=_("Remove saved credentials"))
    credential_fields = ("access_token", "client_id", "client_secret", "api_username", "api_password")
    class Meta:
        model = ChannelIntegration
        fields = ["external_property_id", "account_reference", "authentication_method"]
        labels = {"external_property_id": _("External property / hotel ID"), "account_reference": _("Account reference (optional)")}

    def __init__(self, *args, property_obj, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.property_profile = property_obj
        self.units = list(Unit.objects.filter(property_profile=property_obj).order_by("code")) if property_obj else []
        mappings = self.instance.unit_mappings or {}
        for unit in self.units:
            mapping = mappings.get(str(unit.pk), {})
            self.fields[f"unit_{unit.pk}_room"] = forms.CharField(required=False, max_length=120, initial=mapping.get("room_id", ""), label=_("Room / listing ID"))
            self.fields[f"unit_{unit.pk}_rate"] = forms.CharField(required=False, max_length=120, initial=mapping.get("rate_plan_id", ""), label=_("Rate plan ID (if applicable)"))
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control", "autocomplete": "new-password" if isinstance(field.widget, forms.PasswordInput) else "off"})
        self.storage_ready = credential_storage_ready()
        self.fields["authentication_method"].required = False

    def clean_authentication_method(self):
        return self.cleaned_data.get("authentication_method") or self.instance.authentication_method

    @property
    def credential_inputs(self):
        return [self[name] for name in self.credential_fields]

    def clean(self):
        cleaned = super().clean()
        changes = {name: cleaned[name] for name in self.credential_fields if cleaned.get(name)}
        self._credentials = None
        if cleaned.get("clear_credentials"):
            self._credentials = {}
        if changes:
            if not self.storage_ready:
                raise forms.ValidationError(_("Secure credential storage is not configured. Ask your administrator to set CHANNEL_CREDENTIALS_KEY before entering API credentials."))
            try:
                self._credentials = {} if cleaned.get("clear_credentials") else self.instance.get_credentials()
            except Exception:
                raise forms.ValidationError(_("Existing credentials cannot be decrypted. Restore the encryption key or remove saved credentials before replacing them."))
            self._credentials.update(changes)
        return cleaned

    @property
    def unit_rows(self):
        return [{"unit": u, "room": self[f"unit_{u.pk}_room"], "rate": self[f"unit_{u.pk}_rate"]} for u in self.units]

    def save(self, commit=True):
        if self._credentials is not None:
            self.instance.set_credentials(self._credentials)
        self.instance.unit_mappings = {
            str(u.pk): {"room_id": self.cleaned_data[f"unit_{u.pk}_room"], "rate_plan_id": self.cleaned_data[f"unit_{u.pk}_rate"]}
            for u in self.units if self.cleaned_data[f"unit_{u.pk}_room"] or self.cleaned_data[f"unit_{u.pk}_rate"]
        }
        return super().save(commit=commit)
