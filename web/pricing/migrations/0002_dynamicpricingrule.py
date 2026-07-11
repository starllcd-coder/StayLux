from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("settings_app", "0004_alter_propertyprofile_currency"),
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DynamicPricingRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_enabled", models.BooleanField(default=True)),
                ("base_adjustment_pct", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=5)),
                ("weekend_adjustment_pct", models.DecimalField(decimal_places=2, default=Decimal("8.00"), max_digits=5)),
                ("high_occupancy_threshold", models.PositiveSmallIntegerField(default=80)),
                ("high_occupancy_adjustment_pct", models.DecimalField(decimal_places=2, default=Decimal("12.00"), max_digits=5)),
                ("low_occupancy_threshold", models.PositiveSmallIntegerField(default=40)),
                ("low_occupancy_adjustment_pct", models.DecimalField(decimal_places=2, default=Decimal("-8.00"), max_digits=5)),
                ("seasonal_peak_months", models.CharField(blank=True, default="6,7,8,12", max_length=40)),
                ("seasonal_peak_adjustment_pct", models.DecimalField(decimal_places=2, default=Decimal("10.00"), max_digits=5)),
                (
                    "property_profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dynamic_pricing_rule",
                        to="settings_app.propertyprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="dynamicpricingrule",
            index=models.Index(fields=["is_enabled"], name="pricing_dyna_is_enab_6e4bd4_idx"),
        ),
    ]
