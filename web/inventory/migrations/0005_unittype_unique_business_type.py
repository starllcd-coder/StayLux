from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_unittype_amenities"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="unittype",
            unique_together={("property_profile", "business_type", "name_en")},
        ),
    ]
