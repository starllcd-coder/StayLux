from django.urls import path
from .print_views import invoice_print_view

urlpatterns = [
    path("invoice/<int:invoice_id>/", invoice_print_view, name="print-invoice"),
]