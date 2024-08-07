from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from django.contrib.auth.models import AnonymousUser

    from users.models import User


UserOrAnon: TypeAlias = "User | AnonymousUser"


def user_or_none(user: UserOrAnon | None) -> User | None:
    from users.models import User

    if isinstance(user, User):
        return user
    return None
