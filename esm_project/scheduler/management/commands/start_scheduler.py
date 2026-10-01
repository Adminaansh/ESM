from django.core.management.base import BaseCommand
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start the scheduler loop in a standalone process (keeps running until stopped)'

    def handle(self, *args, **options):
        # Import here so Django settings are initialized
        from scheduler.tasks import start_scheduler_thread, stop_scheduler_thread

        self.stdout.write('Starting scheduler thread...')
        start_scheduler_thread()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write('Stopping scheduler...')
            try:
                stop_scheduler_thread()
            except Exception:
                pass
            self.stdout.write('Scheduler stopped')
