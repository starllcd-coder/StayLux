from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboxmessage",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="outboxmessage",
            index=models.Index(fields=["property_profile", "is_read"], name="notifications_outbox_read_idx"),
        ),
    ]
