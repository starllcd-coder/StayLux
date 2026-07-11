from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mobile_api", "0005_property_experience_media"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobilecustomer",
            name="email_notifications_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="mobilecustomer",
            name="push_notifications_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="mobilecustomer",
            name="sms_notifications_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="MobilePaymentMethod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("brand", models.CharField(max_length=40)),
                ("last4", models.CharField(max_length=4)),
                ("exp_month", models.PositiveSmallIntegerField()),
                ("exp_year", models.PositiveSmallIntegerField()),
                ("provider_token", models.CharField(blank=True, default="", max_length=255)),
                ("is_default", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_methods",
                        to="mobile_api.mobilecustomer",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_default", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="mobilepaymentmethod",
            index=models.Index(fields=["customer", "is_default"], name="mobile_api__customer_1d88dc_idx"),
        ),
        migrations.AddIndex(
            model_name="mobilepaymentmethod",
            index=models.Index(fields=["customer", "is_active"], name="mobile_api__customer_026d85_idx"),
        ),
    ]
