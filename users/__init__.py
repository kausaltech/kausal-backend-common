from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    from users.models import User


type UserOrAnon = "AbstractBaseUser | AnonymousUser"


def is_authenticated(user: UserOrAnon) -> TypeGuard[User]:
    return user.is_authenticated


def user_or_none(user: UserOrAnon | None) -> User | None:
    if user is None:
        return None
    if is_authenticated(user):
        return user
    return None
