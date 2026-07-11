from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TravelerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=200)),
                ("phone", models.CharField(blank=True, default="", max_length=50)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("nationality", models.CharField(blank=True, default="", max_length=100)),
                ("id_type", models.CharField(choices=[("national_id", "National ID"), ("passport", "Passport"), ("driving_license", "Driving License")], default="passport", max_length=20)),
                ("id_number", models.CharField(blank=True, default="", max_length=100)),
                ("id_expiry", models.DateField(blank=True, null=True)),
                ("is_default", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="travelers",
                        to="auth.mobilecustomer",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_default", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="travelerprofile",
            index=models.Index(fields=["customer", "is_default"], name="mobile_api__custome_6c0161_idx"),
        ),
        migrations.AddIndex(
            model_name="travelerprofile",
            index=models.Index(fields=["customer", "is_active"], name="mobile_api__custome_5b0d6d_idx"),
        ),
        migrations.AddIndex(
            model_name="travelerprofile",
            index=models.Index(fields=["customer", "full_name"], name="mobile_api__custome_8776bb_idx"),
        ),
    ]