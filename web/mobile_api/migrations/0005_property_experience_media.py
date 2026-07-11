from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mobile_api", "0004_wishlist_collections_and_payment_security"),
        ("settings_app", "0004_alter_propertyprofile_currency"),
    ]

    operations = [
        migrations.CreateModel(
            name="PropertyExperienceMedia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("media_type", models.CharField(choices=[("image", "Image"), ("video", "Video"), ("tour", "3D Tour")], default="image", max_length=20)),
                ("title", models.CharField(blank=True, default="", max_length=140)),
                ("url", models.URLField(max_length=500)),
                ("thumbnail_url", models.URLField(blank=True, default="", max_length=500)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "property_profile",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="experience_media", to="settings_app.propertyprofile"),
                ),
            ],
            options={"ordering": ["sort_order", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="propertyexperiencemedia",
            index=models.Index(fields=["property_profile", "media_type", "is_active"], name="mobile_api__propert_0ef0f7_idx"),
        ),
    ]
