from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

from django.contrib.auth.models import AnonymousUser

if TYPE_CHECKING:
    from django.contrib.auth.base_user import AbstractBaseUser

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


def user_or_anon(user: AbstractBaseUser | AnonymousUser | None) -> User | AnonymousUser:
    from users.models import User

    if user is None:
        return AnonymousUser()
    if is_authenticated(user):
        assert isinstance(user, User)
        return user
    return AnonymousUser()


def user_or_bust(user: AbstractBaseUser | AnonymousUser | None) -> User:
    if user is None:
        raise ValueError('User is None')
    if is_authenticated(user):
        return user
    raise ValueError('User is not authenticated')
