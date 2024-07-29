def monkeypatch_generic_support():
    import django_stubs_ext
    from wagtail.admin.viewsets.model import ModelViewSet
    from wagtail.permission_policies.base import ModelPermissionPolicy

    django_stubs_ext.monkeypatch([ModelViewSet, ModelPermissionPolicy])
