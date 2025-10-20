"""Django urlpatterns declaration for nautobot_netbox_importer app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView

app_name = "nautobot_netbox_importer"

urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_netbox_importer/docs/index.html")), name="docs"),
]
