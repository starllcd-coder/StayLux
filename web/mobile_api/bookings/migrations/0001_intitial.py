from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MobilePaymentRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("booking_id", models.PositiveIntegerField(blank=True, null=True)),
                ("provider", models.CharField(blank=True, default="", max_length=50)),
                ("provider_reference", models.CharField(blank=True, default="", max_length=255)),
                ("currency", models.CharField(default="OMR", max_length=10)),
                ("amount", models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("requires_action", "Requires Action"), ("paid", "Paid"), ("failed", "Failed"), ("cancelled", "Cancelled"), ("refunded", "Refunded")], default="pending", max_length=20)),
                ("payment_method", models.CharField(blank=True, default="", max_length=50)),
                ("client_secret", models.CharField(blank=True, default="", max_length=255)),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_records",
                        to="auth.mobilecustomer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="mobilepaymentrecord",
            index=models.Index(fields=["customer", "status"], name="mobile_api__custome_f835f0_idx"),
        ),
        migrations.AddIndex(
            model_name="mobilepaymentrecord",
            index=models.Index(fields=["booking_id"], name="mobile_api__booking_2f8fb6_idx"),
        ),
        migrations.AddIndex(
            model_name="mobilepaymentrecord",
            index=models.Index(fields=["provider_reference"], name="mobile_api__provide_0a5922_idx"),
        ),
    ]