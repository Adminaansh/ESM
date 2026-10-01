from django.apps import AppConfig
import sys
import os

class SchedulerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'

    def ready(self):
        # Do not auto-start the scheduler during Django's development `runserver`.
        # Start only when running under a production WSGI server like gunicorn/uwsgi.
        if any(arg in sys.argv for arg in ['gunicorn', 'uwsgi']):
            try:
                from .tasks import start_scheduler_thread
                start_scheduler_thread()
            except Exception:
                pass
