# apps/backend/invoice/urls.py

from django.urls import path

from invoice.views import SharedInvoiceView


app_name = "invoice"

urlpatterns = [
    path(
        "share/<str:token>/",
        SharedInvoiceView.as_view(),
        name="shared-view",
    ),
]