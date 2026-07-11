from django.db import migrations


def normalize_payment_direction(apps, schema_editor):
    Payment = apps.get_model("billing", "Payment")
    # Normalize any stored direction values that are not the canonical 'in'/'out'
    qs = Payment.objects.exclude(direction__in=["in", "out"])[:]
    for p in qs:
        raw = (p.direction or "").strip().lower()
        if raw in ("money in", "money_in", "in"):
            p.direction = "in"
            p.save(update_fields=["direction"])
        elif raw in ("money out (refund)", "money_out", "out"):
            p.direction = "out"
            p.save(update_fields=["direction"])
        else:
            # Unknown value — skip so operator can inspect later
            continue


def reverse_func(apps, schema_editor):
    # Irreversible normalization — do nothing on reverse migration
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_payment_direction_alter_invoice_invoice_no"),
    ]

    operations = [
        migrations.RunPython(normalize_payment_direction, reverse_func),
    ]
