from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from users.models import User
    from django.contrib.auth.models import AnonymousUser


UserOrAnon: TypeAlias = "User | AnonymousUser"


def user_or_none(user: UserOrAnon | None) -> User | None:
    if isinstance(user, User):
        return user
    return None
