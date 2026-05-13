from __future__ import annotations

import strawberry_django
from strawberry import auto

from users.models import User


@strawberry_django.type(User, name='User', description='A user of the system')
class UserNode:
    id: auto
    email: auto
    first_name: auto
    last_name: auto
    is_superuser: auto
    uuid: auto
