"""ContentTypes model class for nautobot-netbox-importer."""
# pylint: disable=too-many-ancestors
from django.contrib.contenttypes import models

from .abstract import NautobotBaseModel


class ContentType(NautobotBaseModel):
    """A reference to a model type, in the form (<app_label>, <modelname>)."""

    _modelname = "contenttype"
    _identifiers = ("app_label", "model")
    _nautobot_model = models.ContentType

    app_label: str
    model: str
