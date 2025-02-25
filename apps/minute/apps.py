from django.apps import AppConfig


class MinuteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.minute"

    def ready(self):
        import apps.minute.signals  #