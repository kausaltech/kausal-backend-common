from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry_django

from users.models import User

if TYPE_CHECKING:
    from strawberry import auto


@strawberry_django.type(User, name='User')
class UserNode:
    id: auto
    email: auto
    first_name: auto
    last_name: auto
    is_superuser: auto
    uuid: auto
