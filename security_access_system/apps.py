# security_access_system/apps.py
from django.apps import AppConfig

class SecurityAccessSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'security_access_system'

    def ready(self):
        import threading
        from .access_control import main

        thread = threading.Thread(target=main, daemon=True, name="AccessControlThread")
        thread.start()