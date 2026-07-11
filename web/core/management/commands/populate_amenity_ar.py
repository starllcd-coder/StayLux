from django.core.management.base import BaseCommand

from inventory.models import Amenity
from django.db import models


class Command(BaseCommand):
    help = "Populate Amenity.name_ar using a fallback mapping for empty Arabic names"

    MAPPING = {
        "Living area (basic seating)": "مساحة جلوس",
        "TV": "تلفاز",
        "Compact kitchenette": "مطبخ صغير",
        "Basic cookware and utensils": "أدوات طهي أساسية",
        "Basic toiletries": "مستلزمات استحمام أساسية",
        "Furnished bedroom": "غرفة نوم مفروشة",
        "Air conditioning": "تكييف",
        "Air conditioning / Heating": "تكييف/تدفئة",
        "Free Wi-Fi": "واي فاي مجاني",
        "Refrigerator": "ثلاجة",
        "Shower bathroom": "دش",
        "Weekly housekeeping": "تنظيف أسبوعي",
        "Smart TV": "تلفاز ذكي",
        "Fully equipped kitchen": "مطبخ مجهز بالكامل",
        "Washing machine": "غسالة",
        "Hair dryer": "مجفف شعر",
        "Housekeeping 2-3 times per week": "تنظيف 2-3 مرات في الأسبوع",
        "Spacious living area": "مساحة معيشة واسعة",
        "Dedicated dining space": "منطقة طعام مخصصة",
        "Microwave and electric stove": "ميكروويف وموقد كهربائي",
        "Iron and ironing board": "مكواة ولوح كي",
        "Faster Wi-Fi": "واي فاي أسرع",
        "Designer interiors": "تصاميم داخلية",
        "Luxury or penthouse apartment": "شقة فاخرة",
        "Private terrace": "شرفة خاصة",
        "Jacuzzi or spa bath": "جاكوزي أو حوض سبا",
        "Complimentary minibar": "ميني بار مجاني",
        "Airport transfers": "نقل من المطار",
        "Airport pickup and drop-off": "التقاط وتسليم المطار",
        "Access to gym, pool and spa": "إمكانية الوصول إلى صالة رياضية وحمام سباحة وسبا",
        "Access to spa, gym, pool and lounge": "إمكانية الوصول إلى السبا والصالة وحمام السباحة",
        "Balcony": "شرفة",
        "Balcony or city/sea view": "شرفة أو إطلالة على المدينة/البحر",
        "Full kitchen with oven": "مطبخ كامل مع فرن",
        "Washing machine and dryer": "غسالة ومجفف",
        "Premium toiletries": "مستلزمات استحمام فاخرة",
        "Dedicated guest support": "دعم ضيوف مخصص",
        "Large living and dining area": "مساحة معيشة وطعام كبيرة",
        "Premium furniture": "أثاث فاخر",
        "Dishwasher": "غسالة صحون",
        "Bathtub or rain shower": "حوض استحمام أو دش مطري",
        "Weekly deep cleaning": "تنظيف عميق أسبوعي",
        "Personal concierge": "كونسيرج خاص",
        "Daily housekeeping": "تنظيف يومي",
        "Panoramic views": "إطلالات بانورامية",
        "Smart home automation": "أتمتة المنزل الذكي",
        "High-end kitchen appliances": "أجهزة مطبخ عالية الجودة",
        "Jacuzzi / spa bathtub": "جاكوزي / حوض سبا",
        "Larger room or improved layout": "غرفة أكبر أو تصميم محسّن",
        "Limited room service": "خدمة غرف محدودة",
        "Luxury bath products": "مستحضرات استحمام فاخرة",
        "Premium mattress and bedding": "مرتبة وبياضات فاخرة",
        "Basic toiletries (soap, shampoo)": "مستلزمات استحمام (صابون، شامبو)",
        "Bathrobes and slippers": "روب ونعال",
        "Better-quality toiletries": "مستلزمات استحمام بجودة أعلى",
        "Coffee and tea maker": "صانعة القهوة والشاي",
        "Comfortable bed and basic linens": "سرير مريح وبياضات أساسية",
        "Concierge assistance": "مساعدة الكونسيرج",
        "Daily or alternate-day housekeeping": "تنظيف يومي أو يوم بعد يوم",
        "Daily turndown service": "خدمة ترتيب السرير اليومية",
        "Designer furniture": "أثاث مصمم",
        "Extended room service": "خدمة غرف موسعة",
        "Front desk / reception support": "دعم مكتب الاستقبال",
        "Mini fridge": "ثلاجة صغيرة",
        "Priority check-in / late check-out (subject to availability)": "أولوية تسجيل الوصول/تأخير المغادرة (حسب التوافر)",
        "Private balcony or terrace": "شرفة أو تراس خاص",
        "Seating area / sofa": "منطقة جلوس / أريكة",
        "Smart TV / international channels": "تلفاز ذكي / قنوات دولية",
        "Smart room controls (lights, AC, curtains)": "تحكم ذكي بالغرفة (إضاءة، تكييف، ستائر)",
        "Suite or luxury room layout": "جناح أو تصميم غرفة فاخرة",
        "TV (local channels)": "تلفاز (قنوات محلية)",
        "Towels": "مناشف",
        "Wardrobe / closet": "دولاب / خزانة",
        "Work desk or side table": "مكتب عمل أو طاولة جانبية",
        "Work desk with ergonomic chair": "مكتب عمل مع كرسي مريح",
    }

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Persist changes to the database")

    def handle(self, *args, **options):
        commit = options.get("commit")
        qs = Amenity.objects.filter(models.Q(name_ar__isnull=True) | models.Q(name_ar=""))
        total = qs.count()
        updated = 0
        self.stdout.write(f"Found {total} amenities with empty Arabic names")
        for a in qs:
            mapping = self.MAPPING.get(a.name_en)
            if mapping:
                self.stdout.write(f"- {a.name_en} -> {mapping}")
                if commit:
                    a.name_ar = mapping
                    a.save(update_fields=["name_ar"])
                updated += 1
            else:
                self.stdout.write(f"- {a.name_en} -> no mapping")

        self.stdout.write(f"Mapped {updated} amenities")
        if not commit:
            self.stdout.write(self.style.WARNING("Run with --commit to persist changes."))
