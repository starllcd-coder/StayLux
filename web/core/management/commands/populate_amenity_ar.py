from django.core.management.base import BaseCommand

from inventory.models import Amenity
from inventory.amenity_names import AMENITY_AR_NAMES
from inventory.text import repair_arabic_encoding


class Command(BaseCommand):
    help = "Populate Amenity.name_ar using a fallback mapping for empty Arabic names"

    MAPPING = AMENITY_AR_NAMES

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Persist changes to the database")

    def handle(self, *args, **options):
        commit = options.get("commit")
        qs = Amenity.objects.all()
        total = qs.count()
        updated = 0
        self.stdout.write(f"Found {total} amenities to check")
        for a in qs:
            mapping = repair_arabic_encoding(a.name_ar) if a.name_ar else self.MAPPING.get(a.name_en)
            if mapping == a.name_ar:
                continue
            if mapping:
                self.stdout.write(f"- {a.name_en}: Arabic label repaired")
                if commit:
                    a.name_ar = mapping
                    a.save(update_fields=["name_ar"])
                updated += 1
            else:
                self.stdout.write(f"- {a.name_en} -> no mapping")

        self.stdout.write(f"Mapped {updated} amenities")
        if not commit:
            self.stdout.write(self.style.WARNING("Run with --commit to persist changes."))
