from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_alter_unit_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="unittype",
            name="amenities",
            field=models.ManyToManyField(blank=True, related_name="unit_types", to="inventory.amenity"),
        ),
    ]
