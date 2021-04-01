"""ContentTypes model class for nautobot-netbox-importer."""
# pylint: disable=too-many-ancestors

from django.contrib.contenttypes import models

from .abstract import DjangoBaseModel


class ContentType(DjangoBaseModel):
    """A reference to a model type, in the form (<app_label>, <modelname>)."""

    _modelname = "contenttype"
    _identifiers = ("app_label", "model",)
    _attributes = ("pk",)
    _nautobot_model = models.ContentType

    app_label: str
    model: str

    def __init__(self, *args, app_label=None, model=None, **kwargs):
        """Map NetBox 'auth.user' content type to Nautobot 'users.user' content type."""
        if app_label == "auth" and model == "user":
            app_label = "users"
        super().__init__(*args, app_label=app_label, model=model, **kwargs)
