# apps/backend/backend/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
#from graphene_django.views import GraphQLView

from .views import purchase_pdf_view
  # Remove (or leave if used elsewhere):
# from graphene_django.views import GraphQLView
from payment.canonical.views import paystack_webhook
from backend.graphql_view import LoggingGraphQLView


urlpatterns = [
    
    # Admin
    path('admin/', admin.site.urls),
    
    # GraphQL API - handle both with and without trailing slash
    #re_path(r'^graphql/?$', csrf_exempt(GraphQLView.as_view(graphiql=True))),
  
    re_path(r'^graphql/?$', csrf_exempt(LoggingGraphQLView.as_view(graphiql=True))),
    path("invoice/", include("invoice.urls")),
   
    # Ecommerce - Support both purchase_id and invoice_id
    path("receipts/pdf/purchase/<uuid:purchase_id>/", purchase_pdf_view, name="purchase-pdf"),
    path("receipts/pdf/invoice/<uuid:invoice_id>/", purchase_pdf_view, name="invoice-pdf"),
    
    # Legacy support - keep old URL for backward compatibility
    path("receipts/pdf/", purchase_pdf_view, name="purchase-pdf-legacy"),
    
    # SEO
    path('robots.txt', cache_page(86400)(TemplateView.as_view(
        template_name="robots.txt",
        content_type="text/plain"))),
    
    path(
        "webhooks/paystack/",
        paystack_webhook,
        name="paystack-webhook",
    ),
]

# Serve media during development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)