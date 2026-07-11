from django.core.management.base import BaseCommand

from sync_engine.services import push_pending_events


class Command(BaseCommand):
    help = "Push pending offline sync events to configured remote backend."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args, **options):
        limit = max(1, min(int(options.get("limit") or 200), 1000))
        summary = push_pending_events(limit=limit)
        self.stdout.write(self.style.SUCCESS(str(summary)))
