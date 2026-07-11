from django.urls import path

from .views import OccupancyReportView, OwnerUnitsDashboardView, OwnerDashboardView
from .exports import export_bookings_xlsx, export_bookings_pdf  # ✅ NEW

urlpatterns = [
    path("dashboard/", OwnerDashboardView.as_view(), name="reports-dashboard"),
    path("occupancy/", OccupancyReportView.as_view(), name="reports-occupancy"),
    path("owner-dashboard/", OwnerUnitsDashboardView.as_view(), name="reports-owner-dashboard"),

    # ✅ Exports
    path("export-bookings.xlsx", export_bookings_xlsx, name="reports-export-bookings-xlsx"),
    path("export-bookings.pdf", export_bookings_pdf, name="reports-export-bookings-pdf"),
]

# Optional endpoints (won't break if the views don't exist yet)
try:
    from .views import RevenueReportView
    urlpatterns += [
        path("revenue/", RevenueReportView.as_view(), name="reports-revenue"),
    ]
except ImportError:
    pass

try:
    from .views import AgingReportView
    urlpatterns += [
        path("aging/", AgingReportView.as_view(), name="reports-aging"),
    ]
except ImportError:
    pass

try:
    from .views import BookingsSummaryView
    urlpatterns += [
        path("bookings-summary/", BookingsSummaryView.as_view(), name="reports-bookings-summary"),
    ]
except ImportError:
    pass