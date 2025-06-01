from django.apps import AppConfig
import threading
import os

class NotificationServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notification_service'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':  # Avoid duplicate starts
            from .consumers import start_notification_service
            print("Starting Notification Service...")
            thread = threading.Thread(target=start_notification_service, daemon=True)
            thread.start()
