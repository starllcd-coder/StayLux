from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SyncConfig",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("enabled", models.BooleanField(default=True)),
                ("mode", models.CharField(choices=[("offline", "Offline"), ("online", "Online"), ("auto", "Auto")], default="auto", max_length=20)),
                ("remote_base_url", models.CharField(blank=True, default="", max_length=255)),
                ("api_token", models.CharField(blank=True, default="", max_length=255)),
                ("shared_secret", models.CharField(blank=True, default="", max_length=255)),
                ("push_enabled", models.BooleanField(default=True)),
                ("pull_enabled", models.BooleanField(default=False)),
                ("interval_seconds", models.PositiveIntegerField(default=30)),
                ("node_id", models.CharField(blank=True, default="", max_length=100)),
                ("last_sync_at", models.DateTimeField(blank=True, null=True)),
                ("last_success_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
            ],
            options={
                "verbose_name": "Sync Configuration",
                "verbose_name_plural": "Sync Configuration",
            },
        ),
        migrations.CreateModel(
            name="SyncEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_node", models.CharField(blank=True, default="", max_length=100)),
                ("model_label", models.CharField(max_length=120)),
                ("object_pk", models.CharField(max_length=80)),
                ("operation", models.CharField(max_length=20)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("synced", "Synced"), ("failed", "Failed")], default="pending", max_length=20)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
            ],
            options={
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(fields=["status", "created_at"], name="sync_engine__status_72c4ac_idx"),
                    models.Index(fields=["model_label", "object_pk"], name="sync_engine__model_l_ebf40b_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SyncInboundEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_uuid", models.UUIDField()),
                ("source_node", models.CharField(blank=True, default="", max_length=100)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("is_processed", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["is_processed", "created_at"], name="sync_engine__is_pro_752f53_idx")],
                "unique_together": {("event_uuid", "source_node")},
            },
        ),
    ]
