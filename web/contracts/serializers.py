from rest_framework import serializers
from .models import Contract, ContractDocument


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = [
            "id",
            "property_profile",
            "unit",
            "guest",
            "status",
            "contract_no",
            "start_date",
            "end_date",
            "monthly_rent",
            "billing_day",
            "currency",
            "security_deposit",
            "deposit_received",
            "deposit_refunded",
            "deposit_status",
            "deposit_invoice",
            "move_out_date",
            "termination_reason",
            "terminated_at",
            "notes",
            "last_invoiced_month",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "deposit_status",
            "deposit_invoice",
            "terminated_at",
            "last_invoiced_month",
            "created_at",
            "updated_at",
        )


class ContractDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ContractDocument
        fields = [
            "id",
            "property_profile",
            "contract",
            "doc_type",
            "title",
            "file",
            "file_url",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("file_url", "created_at", "updated_at")

    def get_file_url(self, obj: ContractDocument):
        request = self.context.get("request")
        if not obj.file:
            return None
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url