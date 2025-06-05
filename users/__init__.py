from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser
    from django.contrib.auth.models import AnonymousUser

    from users.models import User


type UserOrAnon = "User | AnonymousUser"


def is_authenticated(user: AbstractBaseUser | AnonymousUser | None) -> TypeGuard[User]:
    if user is None:
        return False
    return user.is_authenticated


def user_or_none(user: AbstractBaseUser | AnonymousUser | None) -> User | None:
    if user is None:
        return None
    if is_authenticated(user):
        return user
    return None
