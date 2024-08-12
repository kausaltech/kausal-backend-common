from django.apps import AppConfig


class KausalCommonConfig(AppConfig):
    name = 'kausal_common'

    def ready(self) -> None:
        from kausal_common.development.monkey import monkeypatch_generic_support
        monkeypatch_generic_support()
        return super().ready()
