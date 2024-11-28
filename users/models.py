from __future__ import annotations

import base64
from functools import cached_property
from typing import TYPE_CHECKING, Any, cast, overload
from uuid import UUID, uuid4

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.db.models import Model
from django.utils.translation import gettext_lazy as _

from kausal_common.models.types import copy_signature

if TYPE_CHECKING:
    from collections.abc import Generator

    from django.contrib.auth.models import Group
    from django.db.models.expressions import Combinable

    from social_django.models import UserSocialAuth

    from kausal_common.models.roles import InstanceSpecificRole, UserPermissionCache
    from kausal_common.models.types import QS, RevMany


class UserManager[UM: BaseUser](DjangoUserManager[UM]):
    def create_superuser(
        self, username: str | None = None, email: str | None = None, password: str | None = None, **extra_fields
    ) -> UM:
        uuid = uuid4()
        if not username:
            username = uuid_to_username(uuid)
        assert username is not None
        extra_fields['uuid'] = uuid
        return super().create_superuser(username, email, password, **extra_fields)


class BaseUser(AbstractUser):
    email: models.EmailField[str | Combinable, str] = models.EmailField(_('email address'), unique=True)
    uuid: models.UUIDField[UUID, UUID] = models.UUIDField(default=uuid4, editable=False, unique=True)

    social_auth: RevMany[UserSocialAuth]

    test_user_expires_at = models.DateTimeField(null=True, blank=True)
    """Users can be created temporarily for testing purposes."""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    autocomplete_search_field = 'email'

    class Meta:
        abstract = True
        ordering = ('id',)

    def natural_key(self) -> tuple[str]:
        # If we don't override this, it will use `get_username()`, which may not always return the email field. The
        # manager's `get_by_natural_key()`, on the other hand, will expect that the natural key is the email field since
        # we specified `USERNAME_FIELD = 'email'`. We can't just override `get_by_natural_key()` because, if I remember
        # correctly, in some places, Django expects this to actually match with field specified in `USERNAME_FIELD`.
        return (self.email,)

    @property
    def is_test_user(self) -> bool:
        return self.test_user_expires_at is not None

    @copy_signature(AbstractUser.save)
    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def clean(self):
        self._make_sure_uuid_is_set()
        if not self.username:
            self.set_username_from_uuid()

    def _make_sure_uuid_is_set(self) -> None:
        if self.uuid is None:
            self.uuid = uuid4()

    def set_username_from_uuid(self):
        self._make_sure_uuid_is_set()
        self.username = uuid_to_username(self.uuid)

    def get_display_name(self):
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'.strip()
        return self.email

    def get_short_name(self):
        if self.first_name:
            return self.first_name
        return self.email

    def get_username(self):
        if not self.username or self.username.startswith('u-'):
            return self.email
        return self.username

    def __str__(self):
        if self.first_name and self.last_name:
            return f'{self.last_name} {self.first_name} ({self.email})'
        return self.email

    def __rich_repr__(self) -> Generator[tuple[str, Any], Any, None]:
        yield 'email', self.email
        yield 'first_name', self.first_name
        yield 'last_name', self.last_name
        yield 'is_superuser', self.is_superuser

    @cached_property
    def cgroups(self) -> QS[Group]:
        return self.groups.all()

    @cached_property
    def perms(self) -> UserPermissionCache:
        from kausal_common.models.roles import UserPermissionCache

        from users.models import User

        return UserPermissionCache(cast(User, self))

    @overload
    def has_instance_role[M: Model](self, role: InstanceSpecificRole[M], obj: M) -> bool: ...

    @overload
    def has_instance_role(self, role: str, obj: Model) -> bool: ...

    def has_instance_role(self, role: str | InstanceSpecificRole[Any], obj: Model) -> bool:
        return self.perms.has_instance_role(role, obj)

    def can_access_admin(self) -> bool:
        if not self.is_active:
            return False
        if not self.is_staff:
            return False
        return True


def uuid_to_username(uuid: UUID | str):
    """
    Convert UUID to username.

    >>> uuid_to_username('00fbac99-0bab-5e66-8e84-2e567ea4d1f6')
    'u-ad52zgilvnpgnduefzlh5jgr6y'

    >>> uuid_to_username(UUID('00fbac99-0bab-5e66-8e84-2e567ea4d1f6'))
    'u-ad52zgilvnpgnduefzlh5jgr6y'
    """

    uuid_data: bytes
    if isinstance(uuid, UUID):
        uuid_data = uuid.bytes
    else:
        uuid_data = UUID(uuid).bytes
    b32coded = base64.b32encode(uuid_data)
    return 'u-' + b32coded.decode('ascii').replace('=', '').lower()


def username_to_uuid(username: str):
    """
    Convert username to UUID.

    >>> username_to_uuid('u-ad52zgilvnpgnduefzlh5jgr6y')
    UUID('00fbac99-0bab-5e66-8e84-2e567ea4d1f6')
    """
    if not username.startswith('u-') or len(username) != 28:
        raise ValueError('Not an UUID based username: %r' % (username,))
    decoded = base64.b32decode(username[2:].upper() + '======')
    return UUID(bytes=decoded)
