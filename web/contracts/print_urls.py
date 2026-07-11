from django.urls import path
from .print_views import contract_agreement_view

urlpatterns = [
    path("<int:contract_id>/agreement/", contract_agreement_view, name="contract-agreement"),
]