from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MobileCustomer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=200)),
                ("mobile", models.CharField(blank=True, default="", max_length=50)),
                ("preferred_language", models.CharField(choices=[("en", "English"), ("ar", "Arabic")], default="en", max_length=10)),
                ("preferred_country", models.CharField(blank=True, default="", max_length=120)),
                ("is_verified", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mobile_customer",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="mobilecustomer",
            index=models.Index(fields=["is_active"], name="mobile_api__is_acti_7d68a8_idx"),
        ),
        migrations.AddIndex(
            model_name="mobilecustomer",
            index=models.Index(fields=["preferred_country"], name="mobile_api__preferr_c5de10_idx"),
        ),
        migrations.AddIndex(
            model_name="mobilecustomer",
            index=models.Index(fields=["preferred_language"], name="mobile_api__preferr_922846_idx"),
        ),
    ]