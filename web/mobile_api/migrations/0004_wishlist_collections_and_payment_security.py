from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mobile_api", "0003_growth_chat_concierge_security"),
    ]

    operations = [
        migrations.CreateModel(
            name="WishlistCollection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("is_public", models.BooleanField(default=False)),
                ("share_token", models.CharField(blank=True, db_index=True, default="", max_length=32)),
                (
                    "customer",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="wishlist_collections", to="mobile_api.mobilecustomer"),
                ),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("customer", "name")},
            },
        ),
        migrations.AddField(
            model_name="wishlistitem",
            name="collection",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="items", to="mobile_api.wishlistcollection"),
        ),
        migrations.AddField(
            model_name="wishlistitem",
            name="last_known_price",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="wishlistitem",
            name="price_alert_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="wishlistitem",
            name="target_price",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True),
        ),
        migrations.AlterUniqueTogether(
            name="wishlistitem",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="wishlistitem",
            constraint=models.UniqueConstraint(fields=("customer", "property_profile", "collection"), name="uniq_wishlist_item_customer_property_collection"),
        ),
        migrations.CreateModel(
            name="MobilePaymentSecurityCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("verification_status", models.CharField(choices=[("pending", "Pending"), ("verified", "Verified"), ("failed", "Failed"), ("review", "Manual Review")], default="pending", max_length=20)),
                ("risk_score", models.PositiveSmallIntegerField(default=0)),
                ("requires_manual_review", models.BooleanField(default=False)),
                ("fraud_flags", models.JSONField(blank=True, default=list)),
                ("verification_notes", models.TextField(blank=True, default="")),
                (
                    "payment",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="security_check", to="mobile_api.mobilepaymentrecord"),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.AddIndex(
            model_name="mobilepaymentsecuritycheck",
            index=models.Index(fields=["verification_status"], name="mobile_api__verifi_988e18_idx"),
        ),
        migrations.AddIndex(
            model_name="mobilepaymentsecuritycheck",
            index=models.Index(fields=["risk_score"], name="mobile_api__risk_sc_610915_idx"),
        ),
    ]
