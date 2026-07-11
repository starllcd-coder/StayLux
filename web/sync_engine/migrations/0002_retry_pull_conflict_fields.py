from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sync_engine", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="syncconfig",
            name="conflict_policy",
            field=models.CharField(default="last_write_wins", max_length=30),
        ),
        migrations.AddField(
            model_name="syncconfig",
            name="last_pull_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="syncconfig",
            name="max_retry_attempts",
            field=models.PositiveIntegerField(default=8),
        ),
        migrations.AddField(
            model_name="syncevent",
            name="is_dead_letter",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="syncevent",
            name="last_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="syncevent",
            name="next_retry_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="syncevent",
            index=models.Index(fields=["is_dead_letter", "next_retry_at"], name="sync_engine__is_dea_8f5766_idx"),
        ),
    ]
