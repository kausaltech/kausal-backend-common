from django.db.models import QuerySet

from kausal_common.graphene import GQLInfo

def query(queryset: QuerySet, info: GQLInfo, **options): ...
