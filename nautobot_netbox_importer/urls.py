"""Django urlpatterns declaration for nautobot_netbox_importer app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

# Uncomment the following line if you have views to import
# from nautobot_netbox_importer import views


router = NautobotUIViewSetRouter()

# Here is an example of how to register a viewset, you will want to replace views.NautobotNetboxImporterUIViewSet with your viewset
# router.register("nautobot_netbox_importer", views.NautobotNetboxImporterUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_netbox_importer/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
