# Generated manually for StayLux feature expansion
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mobile_api", "0002_mobiledevice_propertyreview_wishlistitem"),
        ("settings_app", "0004_alter_propertyprofile_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name="mobilecustomer",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="mobilecustomer",
            name="loyalty_points",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="mobilecustomer",
            name="loyalty_tier",
            field=models.CharField(
                choices=[("bronze", "Bronze"), ("silver", "Silver"), ("gold", "Gold"), ("platinum", "Platinum")],
                default="bronze",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="mobilecustomer",
            name="referral_code",
            field=models.CharField(blank=True, db_index=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="mobilecustomer",
            name="two_factor_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="ChatConversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(blank=True, default="", max_length=200)),
                (
                    "related_property",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="chat_conversations",
                        to="settings_app.propertyprofile",
                    ),
                ),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="ConciergeService",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True, default="")),
                ("base_price", models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="MembershipPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("monthly_fee", models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ("annual_fee", models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ("benefits", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["monthly_fee", "name"]},
        ),
        migrations.CreateModel(
            name="MobileVerificationCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("purpose", models.CharField(choices=[("email_verify", "Email Verify"), ("two_factor", "Two Factor")], max_length=30)),
                ("channel", models.CharField(blank=True, default="email", max_length=20)),
                ("target", models.CharField(blank=True, default="", max_length=255)),
                ("code", models.CharField(max_length=10)),
                ("expires_at", models.DateTimeField()),
                ("is_used", models.BooleanField(default=False)),
                (
                    "customer",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="verification_codes", to="mobile_api.mobilecustomer"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ReferralInvite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("referred_email", models.EmailField(max_length=254)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("rewarded", "Rewarded")], default="pending", max_length=20)),
                ("reward_points", models.PositiveIntegerField(default=0)),
                (
                    "referrer",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="referral_invites", to="mobile_api.mobilecustomer"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CustomerMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("cancelled", "Cancelled"), ("expired", "Expired")], default="active", max_length=20)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("renews_at", models.DateTimeField(blank=True, null=True)),
                (
                    "customer",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="mobile_api.mobilecustomer"),
                ),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="memberships", to="mobile_api.membershipplan")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ConciergeRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("requested_for_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True, default="")),
                ("quote_amount", models.DecimalField(decimal_places=3, default=0, max_digits=10)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("confirmed", "Confirmed"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                (
                    "customer",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="concierge_requests", to="mobile_api.mobilecustomer"),
                ),
                (
                    "property_profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="concierge_requests",
                        to="settings_app.propertyprofile",
                    ),
                ),
                ("service", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="mobile_api.conciergeservice")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("body", models.TextField()),
                ("translated_body", models.TextField(blank=True, default="")),
                ("attachment_url", models.CharField(blank=True, default="", max_length=500)),
                ("is_system", models.BooleanField(default=False)),
                (
                    "conversation",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="mobile_api.chatconversation"),
                ),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_messages", to="mobile_api.mobilecustomer")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddField(
            model_name="chatconversation",
            name="participants",
            field=models.ManyToManyField(related_name="chat_conversations", to="mobile_api.mobilecustomer"),
        ),
        migrations.AddIndex(
            model_name="mobilecustomer",
            index=models.Index(fields=["loyalty_tier"], name="mobile_api__loyalt_3d8a6b_idx"),
        ),
        migrations.AddIndex(
            model_name="mobileverificationcode",
            index=models.Index(fields=["customer", "purpose", "is_used"], name="mobile_api__custome_72ea77_idx"),
        ),
        migrations.AddIndex(
            model_name="mobileverificationcode",
            index=models.Index(fields=["expires_at"], name="mobile_api__expire_3ec544_idx"),
        ),
        migrations.RunPython(
            code=lambda apps, schema_editor: _seed_growth_and_concierge(apps),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def _seed_growth_and_concierge(apps):
    ConciergeService = apps.get_model("mobile_api", "ConciergeService")
    MembershipPlan = apps.get_model("mobile_api", "MembershipPlan")

    services = [
        ("airport_pickup", "Airport Pickup", "Private transfer from/to airport", "15.000"),
        ("car_rental", "Car Rental", "Daily rental with trusted partners", "20.000"),
        ("private_chef", "Private Chef", "In-room dining experience", "40.000"),
        ("guided_tour", "Guided Tour", "Local cultural and city tours", "25.000"),
    ]
    for code, name, description, base_price in services:
        ConciergeService.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "base_price": base_price,
                "is_active": True,
            },
        )

    plans = [
        ("Silver", "5.000", "45.000", ["5% booking discount", "Priority support"]),
        ("Gold", "9.000", "95.000", ["10% booking discount", "Concierge priority", "Early access"]),
    ]
    for name, monthly, annual, benefits in plans:
        MembershipPlan.objects.get_or_create(
            name=name,
            defaults={
                "monthly_fee": monthly,
                "annual_fee": annual,
                "benefits": benefits,
                "is_active": True,
            },
        )
