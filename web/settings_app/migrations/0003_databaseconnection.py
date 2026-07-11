from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("settings_app", "0002_propertyprofile_city_propertyprofile_country_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatabaseConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(default="Primary Database", max_length=120)),
                ("engine", models.CharField(default="django.db.backends.postgresql", max_length=200)),
                ("host", models.CharField(max_length=200)),
                ("port", models.CharField(default="5432", max_length=20)),
                ("db_name", models.CharField(max_length=200)),
                ("username", models.CharField(max_length=200)),
                ("password_enc", models.TextField(blank=True, default="")),
                ("sslmode", models.CharField(default="require", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
