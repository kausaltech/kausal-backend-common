from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model, QuerySet
from django.forms import ValidationError

from loguru import logger

from kausal_common.models.permissions import PermissionedModel, PermissionedQuerySet
from kausal_common.strawberry.errors import NotFoundError

if TYPE_CHECKING:

    import strawberry

    from kausal_common.models.permission_policy import ObjectSpecificAction


logger = logger.bind(markup=True, name='graphql')

type LogLevel = Literal['DEBUG', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'CRITICAL']


def graphql_log(level: LogLevel, operation_name: str | None, msg, *args, depth: int = 0, **kwargs):
    log = logger.opt(depth=1 + depth)
    if operation_name:
        log = log.bind(graphql_operation=operation_name)
    log.log(level, 'GQL request [magenta]%s[/]: %s' % (operation_name, msg), *args, **kwargs)


def get_or_error[M: Model](
    info: strawberry.Info,
    model_or_queryset: type[M] | QuerySet[M],
    id: str | int | None = None,
    for_action: ObjectSpecificAction = 'view',
    field_name: str | None = None,
    **kwargs: Any,
) -> M:
    if isinstance(model_or_queryset, QuerySet):
        qs = model_or_queryset
    else:
        qs = model_or_queryset._default_manager.all()
        assert id is not None or kwargs, "Either id or kwargs must be provided"

    if isinstance(qs, PermissionedQuerySet):
        assert isinstance(qs.model, PermissionedModel)
        qs = qs.filter_by_perm(info.context.user, for_action)

    if id is not None:
        qs = qs.filter(id=id)

    if kwargs:
        qs = qs.filter(**kwargs)

    try:
        obj = qs.get()
    except ObjectDoesNotExist as error:
        msg = f"{qs.model._meta.verbose_name} not found"
        if field_name:
            raise ValidationError({field_name: msg}) from error
        raise NotFoundError(info, msg, original_error=error) from error

    return cast('M', obj)
