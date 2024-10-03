from __future__ import annotations

from typing import TYPE_CHECKING

from rich import print

if TYPE_CHECKING:
    from django.db.models import QuerySet


def print_queryset_sql(qs: QuerySet):
    import sqlparse  # type: ignore[import-untyped]
    from rich.syntax import Syntax

    print("QuerySet for %s" % qs.model)
    sql = sqlparse.format(str(qs.query), reindent=True)
    highlighted = Syntax(sql, 'sql')
    print(highlighted)
