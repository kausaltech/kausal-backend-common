from django.apps import AppConfig


class BudgetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kausal_common.budget'
    label = 'budget'

    def ready(self):
        try:
            import kausal_common.budget.wagtail_admin  # noqa
        except ImportError:
            pass