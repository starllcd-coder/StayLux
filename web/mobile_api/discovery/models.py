from django.db import models

from core.models import TimeStampedModel
from settings_app.models import PropertyProfile


class PropertyExperienceMedia(TimeStampedModel):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        TOUR = "tour", "3D Tour"

    property_profile = models.ForeignKey(
        PropertyProfile,
        on_delete=models.CASCADE,
        related_name="experience_media",
    )
    media_type = models.CharField(max_length=20, choices=MediaType.choices, default=MediaType.IMAGE)
    title = models.CharField(max_length=140, blank=True, default="")
    url = models.URLField(max_length=500)
    thumbnail_url = models.URLField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "media_type", "is_active"]),
        ]
